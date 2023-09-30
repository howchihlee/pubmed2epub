from src import oa_api_helper
from src.oa_parser import *
import os

if __name__ == "__main__":
    pmc_id = 'PMC9169933'
    #pmc_id = 'PMC6823428'
    #pmc_id = 'PMC8778485'

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


    output_dir = 'output'
    toc = create_toc_section(elements, section_title = 'Table of content', list_type = 'ul')            
    ref_content = create_reference_section(tree, section_title = 'References', list_type = 'ol')

    html_content = add_head(toc + body_content + ref_content)
    write_html(html_content, f'{output_dir}/output.html')  
    copy_jpg_files(f'{pmc_id}', f'{output_dir}/figs')

