import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
from contextlib import contextmanager
from xml.etree import ElementTree as ET

import requests
import streamlit as st
from src.oa_api_helper import get_pmc_ftp_url


@contextmanager
def temporary_directory():
    """
    Create and return a temporary directory. This has the same
    behavior as mkdtemp but can be used as a context manager.
    Upon exiting the context, the directory and all its contents
    are removed.
    """
    dirpath = tempfile.mkdtemp()
    try:
        yield dirpath
    finally:
        shutil.rmtree(dirpath)

def get_cache():
    """
    Retrieve or initialize the cache using st.session_state.

    :return: A dictionary serving as the cache.
    :rtype: dict
    """
    if 'cache_data' not in st.session_state:
        st.session_state.cache_data = {}
    return st.session_state.cache_data

def cache_with_expiry(fn, maxsize=100, expiry=3600):
    """
    Decorator to cache function results with a specified expiry.

    :param fn: The function to be decorated.
    :type fn: function
    :param maxsize: Maximum size of cache, defaults to 100.
    :type maxsize: int, optional
    :param expiry: Cache expiration time in seconds, defaults to 3600.
    :type expiry: int, optional
    :return: The decorated function.
    :rtype: function
    """
    def wrapper(pmc_id):
        cache = get_cache()

        # Check if value is in cache and not expired
        if pmc_id in cache and not time.time() - cache[pmc_id]['timestamp'] > expiry:
            return cache[pmc_id]['value']

        # Fetch the fresh value
        result = fn(pmc_id)

        # Cache eviction if needed
        if len(cache) >= maxsize:
            oldest_key = min(cache.keys(), key=lambda k: cache[k]['timestamp'])
            del cache[oldest_key]

        # Store the new value in cache
        cache[pmc_id] = {'value': result, 'timestamp': time.time()}
        return result

    return wrapper

#@cache_with_expiry
def get_articles_summary(pmc_ids: list) -> dict:
    """
    Fetches article summary details using the provided list of PMC IDs.

    :param pmc_ids: A list of PMC IDs for the articles.
    :type pmc_ids: list[str]
    :return: A dictionary where the keys are PMC IDs and the values are dictionaries containing the article title and its open access status.
    :rtype: dict
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi"
    num2pmc_id = {i[3:]:i for i in pmc_ids}
    params = {
        "db": "pmc",
        "id": ",".join(num2pmc_id.keys()),
        "retmode": "json"
    }

    response = requests.get(base_url, params=params)
    data = response.json()

    result = {}
    for pmc_id in num2pmc_id:
        article_details = data.get("result", {}).get(pmc_id, {})
        title = article_details.get("title", "Title not found")
        result[num2pmc_id[pmc_id]] = {
            "title": title,
        }
    return result

def delete_item(item_id):
    """Delete an item from stored_ids by index."""
    st.session_state.stored_ids.remove(item_id)

def is_valid_id(pmc_id: str):
    return pmc_id.startswith('PMC') and get_pmc_ftp_url(pmc_id)[0]

def submit():
    ids = [item.strip() for item in st.session_state.widget.split(",")]
    ids = [pmc_id for pmc_id in ids if is_valid_id(pmc_id)]

    summary_dict = get_articles_summary(ids)
    for pmc_id, details in summary_dict.items():
        st.session_state.stored_ids.add(pmc_id)
        st.session_state.cached_titles[pmc_id] = details['title']
    st.session_state.widget = ""

def execute_command(cmd: list[str]) -> None:
    """
    Execute a subprocess command and write the output or error to Streamlit.

    :param cmd: The command to execute as a list.
    """
    cmd = [f"{sys.executable}"] + cmd
    result = subprocess.run(cmd, capture_output=True, text=True)
    action = cmd[1] if len(cmd) > 1 else cmd[0]
    if result.returncode == 0:
        st.write(f"{action} successfully!")
        st.write(result.stdout)
    else:
        st.write(f"Execution failed: {' '.join(cmd)}")
        st.write(result.stderr)

def run_command(html_dir: str, output_file: str = 'ebook.epub'):
    """Runs an external Python script with arguments."""
    for pmc_id in st.session_state.stored_ids:
        execute_command(["python", "make_pmc_html.py", pmc_id, '--output_dir', html_dir])
    cmd = ["python", "make_epub.py", '--pmc_ids'] + [','.join(st.session_state.stored_ids)]
    cmd += ['--input_dir', html_dir]
    cmd += ['--output_file', output_file]
    execute_command(cmd)

def kepubify(file_name: str):
    execute_command(["./kepubify-linux-64bit", file_name, '-i'])
    #s.system(f'''./kepubify-linux-64bit {file_name} -i''')

def main():
    st.title("Epubify PMC OA articles")
    # Retrieve stored IDs from session state if they exist, or initialize as empty list
    if "stored_ids" not in st.session_state:
        st.session_state.stored_ids = set()
    if 'cached_titles' not in st.session_state:
        st.session_state.cached_titles = {}

    # User input for comma-separated item IDs
    if 'text_input' not in st.session_state:
        st.session_state.text_input = ''

    kepubify_option = st.radio(
        'KOBO friendly format:',
        ('Yes', 'No')
    )

    st.text_input("Enter comma separated PMC IDs", key='widget', on_change=submit)

    # Display details for each stored item ID and provide delete button
    for idx, pmc_id in enumerate(st.session_state.stored_ids):
        title = st.session_state.cached_titles[pmc_id]
        col1, col2 = st.columns([4, 1])  # Adjust these numbers for column width ratio
        col1.write(f"{pmc_id}: {title}")
        # Callback button to delete an individual item
        delete_btn = col2.button("Delete", key = f'delete_{pmc_id}', on_click=delete_item, args=(pmc_id, ))

    col1, col2 = st.columns([4, 1])

    if st.button("Generate EPUB"):
        with temporary_directory() as tmp_dir:
            epub_name = os.path.join(tmp_dir, 'ebook.epub')
            run_command(tmp_dir, epub_name)

            if kepubify_option == 'Yes':
                kepubify(epub_name)
                #epub_name = os.path.join(tmp_dir, 'ebook_converted.kepub.epub')

            # Read the EPUB file in binary mode
            with open(epub_name, "rb") as f:
                binary_data = f.read()

            buffer = io.BytesIO()
            buffer.write(binary_data)
            buffer.seek(0)

            # Stream the EPUB file to the user
            st.download_button(
                label="Download EPUB File",
                data=buffer,
                file_name="ebook.epub",
                mime="application/epub+zip"
            )


if __name__ == "__main__":
    main()
