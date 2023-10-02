import os
import re
import shutil

import lxml
from lxml import etree
from lxml import html as lxml_html


def to_unicode_string(node, method = 'xml'):
    return etree.tostring(node, encoding='unicode', method=method)

def find_files(extension, folder):
    out = []
    for root, dirs, files in os.walk(folder):
        for file in files:
            if file.endswith(f".{extension}"):
                out.append(os.path.join(root, file))
    return out

def copy_jpg_files(src_dir, dest_dir):
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    for file_name in os.listdir(src_dir):
        if file_name.endswith('.jpg') or file_name.endswith('.jpeg'):
            src_file_path = os.path.join(src_dir, file_name)
            dest_file_path = os.path.join(dest_dir, file_name)
            shutil.copy(src_file_path, dest_file_path)

def collect_elements(element, level=0, result=None):
    if result is None:
        result = []
    level += 1
    title_elem = element.find('title')
    if title_elem is None:
        return result

    title = title_elem.text
    sec_id = element.get('id')
    data = {'text': title, 'level': level, 'section':sec_id}
    result.append({'type': element.tag, 'data': data})

    for child in element:
        if child.tag == 'sec':
            collect_elements(child, level, result)
        elif child.tag == 'title':
            continue
        else:
            inner_content = to_unicode_string(child)
            data = {'text': inner_content}
            result.append({'type': child.tag, 'data': data})
    return result

def write_html(html_content, file_name='output.html'):
    # Write the generated HTML content to a file
    with open(file_name, 'w') as f:
        f.write(html_content)

def add_title_page(title, authors, abstract, keywords, main_content):
    html_template = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{title}</title>
        <link rel="stylesheet" type="text/css" href="styles/style.css" />
    </head>
    <body>
        <div class="container">
            <div class="title">{title}</div>
            <div class="authors">Authors: {authors}</div>
            <div class="abstract">
                <strong>Abstract:</strong>
                <div>{abstract}</div>
            </div>
            <div class="keywords">Keywords: {keywords}</div>
        </div>
        <div class="main-content">
            {main_content}
        </div>
    </body>
    </html>
    """
    return html_template.format(
        title=title,
        authors=', '.join(authors),
        abstract=abstract,
        keywords=', '.join(keywords),
        main_content=main_content
    )

def parse_article(tree):
    title = tree.find(".//article-title").text
    authors = []
    for author in tree.findall(".//contrib[@contrib-type='author']"):
        name = author.find('./name')
        given_names = name.find('./given-names').text
        surname = name.find('./surname').text
        authors.append(f'{given_names} {surname}')

    abstract = to_unicode_string(tree.find(".//abstract"))
    keywords = [kwd.text for kwd in tree.findall(".//kwd")]

    title_page = f'''<div class="container">
            <div class="title">{title}</div>
            <div class="authors">Authors: {', '.join(authors)}</div>
            <div class="abstract">
                <strong>Abstract:</strong>
                <div>{abstract}</div>
            </div>
            <div class="keywords">Keywords: {', '.join(keywords)}</div>
        </div>'''
    return title_page, (title, authors, abstract, keywords)

def replace_xref_with_link(xml_string):
    root = etree.fromstring(xml_string)
    xref_elements = root.xpath('.//xref')

    for xref_element in xref_elements:
        a_element = etree.Element('a')
        rid = xref_element.get('rid')
        ref_type = xref_element.get('ref-type')
        if rid:
            a_element.set('href', f'#{rid}')
        if ref_type:
            a_element.set('ref-type', ref_type)

        for child in xref_element:
            a_element.append(child)

        a_element.text = xref_element.text
        a_element.tail = xref_element.tail
        xref_element.getparent().replace(xref_element, a_element)

    html_string = to_unicode_string(root)
    return html_string

def _get_caption(node):
    p_element = node.xpath('./caption/p')
    if p_element:
        return to_unicode_string(p_element[0])
    else:
        return to_unicode_string(node)

def convert_figs(xml_text):
    xml_text = f'<dummyroot>{xml_text}</dummyroot>'
    #parser = etree.XMLParser(recover=True)  # recover from bad characters.
    root = etree.fromstring(xml_text)
    for fig in root.xpath('//fig'):
        fig_id = fig.get('id')
        fig_label = fig.xpath('string(./label)')
        caption_elem = fig.find('caption')
        caption_text = _get_caption(fig)
        fig_url = fig.xpath("./graphic/@*[local-name()='href']")[0]
        # Create the new <figure> element
        figure_elem = etree.Element('figure')
        img_elem = etree.SubElement(figure_elem, 'img', {
            'src': f'figs/{fig_url}.jpg',
            'alt': fig_label,
            'id': fig_id
        })
        #figcaption_elem = etree.SubElement(figure_elem, 'figcaption')
        figcaption_elem = etree.SubElement(figure_elem, 'figcaption')

        # Create an HTML fragment for the figcaption content
        #figcaption_content = f'{fig_label}: {caption_text}'
        figcaption_content = caption_text
        figcaption_fragment = lxml_html.fragment_fromstring(figcaption_content)
        figcaption_elem.append(figcaption_fragment)
        # Replace the old <fig> element with the new <figure> element
        fig.getparent().replace(fig, figure_elem)

    return ''.join([to_unicode_string(child) for child in root])

def create_toc_section(elements, section_title = 'Table of content', list_type = 'ul'):
    assert list_type == 'ol' or list_type == 'ul'
    # Loop through each text and id
    html_output = ''
    for elem in elements:
        if elem['type'] == 'sec':
            text, id_ = elem['data']['text'], elem['data']['section']
            html_output += f'<li><a href="#{id_}">{text}</a></li>\n'
    return add_header_to_list(html_output, section_title, list_type)

def add_header_to_list(html_output, section_title = 'Table of content', list_type = 'ul'):
    # Start the reference section
    head = f'''<h2>{section_title}</h2>\n'''
    if list_type == 'ol':
        head += '<ol>\n'
    else:
        head += '<ol class="no-numbers">\n'

    # Close the ordered list tag
    if list_type == 'ol':
        end = '</ol>\n'
    else:
        end = '</ol>\n'
    return head + html_output + end

def find_text(ref, tag):
    node = ref.find(tag)
    return (node.text or "").strip() if node is not None else ""

def find_names(ref, tag):
    nodes = ref.findall(tag)
    names = []
    for n in nodes:
        if tag == "name":
            name_parts = [t.text or "" for t in n.getchildren()]
            name = " ".join(name_parts[::-1]).strip()
            names.append(name)
        elif tag == "person-group":
            for person in n:
                given_names = person.xpath("given-names/text()")
                surnames = person.xpath("surname/text()")
                name = " ".join(given_names + surnames).strip()
                names.append(name)
    return ', '.join([s for s in names if s])

def get_reference_entry(reference):
    ref_id = reference.attrib.get("id", "")
    mixed_citation = reference.find("mixed-citation")
    element_citation = reference.find("element-citation")
    ref = mixed_citation if mixed_citation is not None else element_citation

    if ref is None:
        return None  # Return None or some other default value if ref is not found

    publication_type = ref.attrib.get("publication-type", "")
    journal_type = next(iter(ref.attrib.values()), "")  # Grab the first attribute value, if any

    names = find_names(ref, "name") or find_names(ref, "person-group")
    article_title = find_text(ref, "article-title").replace("\n", " ").strip()
    journal = find_text(ref, "source")
    year = find_text(ref, "year")

    if article_title != '' or journal != '':
        text = [names, article_title, f'<i>{journal}</i>', year]
        text = ', '.join([s for s in text if s])
    elif publication_type == 'webpage':
        text = to_unicode_string(ref.xpath('.//comment')[0], method='text')
    else:
        text = to_unicode_string(ref, method='text').replace('\n', '')
    return f'<li id="{ref_id}" epub:type="footnote">{text}</li>\n'

def create_reference_section(tree, section_title = 'References', list_type = 'ol'):
    assert list_type == 'ol' or list_type == 'ul'
    references = tree.xpath(".//ref-list/ref[@id]")
    html_output = ''
    for ref in references:
        html_output += get_reference_entry(ref)
    return  add_header_to_list(html_output, section_title, list_type)
