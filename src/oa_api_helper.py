import json
import tarfile
import xml.etree.ElementTree as ET

import requests


def extract_tar_gz(file_path, extract_path='.'):
    # Open the tar.gz file
    with tarfile.open(file_path, 'r:gz') as file:
        # Extract all files into the directory specified by extract_path
        file.extractall(path=extract_path)

def download_file(url, local_filename):
    with requests.get(url, stream=True) as r:
        r.raise_for_status()
        with open(local_filename, 'wb') as f:
            for chunk in r.iter_content(chunk_size=8192):
                f.write(chunk)

def fetch_json_from_url(url: str):
    response = requests.get(url)
    if response.status_code == 200:
        json_data = response.json()
        return json_data
    else:
        return f"Failed to retrieve data. HTTP Status Code: {response.status_code}"

def get_pmc_ftp_url(pmc_id: str) -> (bool, str):
    """
    Checks if a given PMC ID corresponds to an open access article using the provided OA API.

    Parameters:
        - pmc_id (str): The PubMed Central ID to check.

    Returns:
        tuple:
            bool: True if the PMC ID corresponds to an open access article, False otherwise.
            str: FTP address of the open access article package if open access, empty string otherwise.
    """
    BASE_URL = "https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi"
    params = {"id": pmc_id}

    response = requests.get(BASE_URL, params=params)
    tree = ET.fromstring(response.content)

    # Check for the error indicating non-open access
    error_element = tree.find(".//error[@code='idIsNotOpenAccess']")
    if error_element is not None:
        return False, ""

    # Check for the record indicating open access
    assert tree.find('request').attrib['id'] == pmc_id
    record_element = tree.find(".//record")
    if record_element is not None:
        # Extract FTP address for the .tar.gz format
        link_element = record_element.find(".//link[@format='tgz']")
        if link_element is not None:
            ftp_address = link_element.get("href")
            return True, ftp_address

    return False, ""

def pmc_id2pmid(pmc_id: str):
    '''
    input: a string of a PMC_ID
    return
    '''
    url = f'https://www.ncbi.nlm.nih.gov/pmc/utils/idconv/v1.0/?ids={pmc_id}&format=json'
    json_data = fetch_json_from_url(url)
    pmid = [r['pmid'] for r in json_data['records'] if r['pmcid'] == pmc_id][0]
    return pmid

def get_bioc_json(pmid):
    url = f'https://www.ncbi.nlm.nih.gov/research/bionlp/RESTful/pmcoa.cgi/BioC_json/{pmid}/ascii'
    req = requests.get(url)
    reads = json.loads(req.content.decode('utf8'))
    return reads
