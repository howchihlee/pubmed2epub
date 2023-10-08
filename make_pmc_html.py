import argparse
import os

from src import oa_api_helper
from src.oa_parser import *


def create_directory(directory_path):
    try:
        os.makedirs(directory_path)
    except FileExistsError:
        pass
    except Exception as e:
        print(f"An error occurred: {e}")

def main(pmc_id: str, output_dir: str):
    if not os.path.isdir(pmc_id):
        #print(f'{file_path} does not exist.')
        url = oa_api_helper.get_pmc_ftp_url(pmc_id).replace('ftp://', 'https://')
        oa_api_helper.download_file(url, f'{pmc_id}.tar.gz')
        file_path = f'{pmc_id}.tar.gz'
        oa_api_helper.extract_tar_gz(file_path)

    nxml_file = find_files('nxml', f'{pmc_id}')[0]
    with open(nxml_file, 'rb') as file:
        tree = etree.parse(file)
    sections = tree.xpath('//body//sec')
    elements = []
    for sec in sections:
        elements += collect_elements(sec)

    create_directory(os.path.join(output_dir, 'figs'))

    title_div, (title, authors, abstract, keywords) = parse_article(tree)
    toc = create_toc_section(elements, section_title = 'Table of content', list_type = 'ul')

    body_content = ''
    for elem in elements:
        if elem['type'] == 'sec':
            level, text, section_id = elem['data']['level'], elem['data']['text'], elem['data']['section']
            body_content += f'<h{level} id="{section_id}">{text}</h{level}>'
        else:
            text = elem['data']['text']
            text = replace_xref_with_link(text)
            text = convert_figs(text)
            body_content += text

    ref_content = create_reference_section(tree, section_title = 'References', list_type = 'ol')
    main_content = toc + body_content + ref_content
    html_content = add_title_page(title, title_div, main_content)
    write_html(html_content, f'{output_dir}/{pmc_id}.html')
    copy_jpg_files(f'{pmc_id}', f'{output_dir}/figs')
    return

def parse_arguments():
    parser = argparse.ArgumentParser(description='make a html page for a pmc article')
    parser.add_argument('pmc_id', help='pmc id PMCXXXXXX.')
    parser.add_argument('--output_dir',
                        type=str,
                        default='./output',
                        help='Directory to store the output HTML page.')
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_arguments()
    main(args.pmc_id, args.output_dir)
