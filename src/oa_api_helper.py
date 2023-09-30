import requests
import xml.etree.ElementTree as ET
import requests
import tarfile
import json

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

def get_pmc_ftp_url(PMC_ID: str):
    url = f'https://www.ncbi.nlm.nih.gov/pmc/utils/oa/oa.fcgi?id={PMC_ID}'
    response = requests.get(url)
    root = ET.fromstring(response.content)
    assert root.find('request').attrib['id'] == PMC_ID
    return [l.attrib['href'] for l in root.find('records').find('record').findall('link') if l.attrib['format'] == 'tgz'][0]

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
