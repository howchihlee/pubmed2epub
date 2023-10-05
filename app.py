import subprocess
import time
from xml.etree import ElementTree as ET

import requests
import streamlit as st


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

@cache_with_expiry
def get_article_title(pmc_id: str):
    """
    Fetches article details using the provided PMC ID.

    :param pmc_id: The PMC ID for the article.
    :type pmc_id: str
    :return: Article title for the provided PMC ID.
    :rtype: str
    """
    base_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/efetch.fcgi"
    params = {
        "db": "pmc",
        "id": pmc_id,
        "retmode": "xml"
    }

    response = requests.get(base_url, params=params)
    tree = ET.fromstring(response.content)

    # Extracting the title
    title_element = tree.find(".//article-title")
    title = title_element.text
    return title

def delete_item(item_id):
    """Delete an item from stored_ids by index."""
    st.session_state.stored_ids.remove(item_id)

def submit():
    ids = [item.strip() for item in st.session_state.widget.split(",") if item.startswith('PMC')]
    st.session_state.stored_ids.update(ids)
    st.session_state.widget = ""

def run_command():
    """Runs an external Python script with arguments."""
    for pmc_id in st.session_state.stored_ids:
        cmd = ["python", "make_pmc_html.py", pmc_id]
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            st.write(f"{' '.join(cmd)} executed successfully!")
            st.write(result.stdout)
        else:
            st.write("Script execution failed!")
            st.write(result.stderr)
    cmd = ["python", "make_epub.py", '--pmc_ids'] + [','.join(st.session_state.stored_ids)]
    subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        st.write(f"{' '.join(cmd)} executed successfully!")
        st.write(result.stdout)
    else:
        st.write("Script execution failed!")
        st.write(result.stderr)

def main():
    st.title("Item Lookup App")
    # Retrieve stored IDs from session state if they exist, or initialize as empty list
    if "stored_ids" not in st.session_state:
        st.session_state.stored_ids = set()

    # User input for comma-separated item IDs
    if 'text_input' not in st.session_state:
        st.session_state.text_input = ''

    st.text_input("Enter comma separated PMC IDs", key='widget', on_change=submit)

    # Display details for each stored item ID and provide delete button
    for idx, pmc_id in enumerate(st.session_state.stored_ids):
        title = get_article_title(pmc_id)
        col1, col2 = st.columns([4, 1])  # Adjust these numbers for column width ratio
        col1.write(f"{pmc_id}: {title}")
        # Callback button to delete an individual item
        delete_btn = col2.button("Delete", key = f'delete_{pmc_id}', on_click=delete_item, args=(pmc_id, ))
    # Button to run a command in terminal
    if st.button("Run Command"):
        run_command()

if __name__ == "__main__":
    main()
