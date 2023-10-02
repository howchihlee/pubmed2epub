import argparse
import glob

from ebooklib import epub


def main(pmc_ids, html_dir:str,  output_file:str, css_file:str = './styles/style.css'):
    book = epub.EpubBook()
    # set metadata
    book.set_identifier("id123456")
    book.set_title("Pubmed paper collection")
    book.set_language("en")
    book.add_author("Awesome author")

    toc = []
    chapters = []
    for i, pmc_id in enumerate(pmc_ids):
        with open(f'{html_dir}/{pmc_id}.html', 'r', encoding='utf-8') as f:
            html_content = f.read()

        # create chapter
        c1 = epub.EpubHtml(title=f"{pmc_id}", file_name=f"{pmc_id}.xhtml", lang="en")
        c1.content = (html_content)

        book.add_item(c1)
        chapters.append(c1)
        toc.append(epub.Link(f"{pmc_id}.xhtml", pmc_id, pmc_id))

    ## move this part to separate pmc_id directories later
    fig_files = glob.glob(f"{html_dir}/figs/*.jpg", recursive=True)
    for fn in fig_files:
        with open(fn, "rb") as reader:
            image_content = reader.read()
            ei = epub.EpubImage()
            ei.file_name = f"figs/{fn.split('/')[-1]}"
            ei.media_type = 'image/jpg'
            ei.content = image_content
            book.add_item(ei)

    # define Table Of Contents
    book.toc = tuple(toc)

    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # define CSS style
    with open(css_file, 'r', encoding='utf-8') as file:
        style = file.read()

    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name=f"style/style.css",
        media_type="text/css",
        content=style,
    )

    # add CSS file
    book.add_item(nav_css)

    # basic spine
    book.spine = ["nav"] + chapters

    # write to the file
    epub.write_epub(output_file, book)

def parse_arguments():
    parser = argparse.ArgumentParser(description='Process PMC IDs and specify output file.')
    parser.add_argument('--pmc_ids', type=str, required=True, help='The PMC IDs to be processed. IDs are comma separated')
    parser.add_argument('--output_file', type=str, default='ebook.epub', help='The file to write output to.')
    return parser.parse_args()

if __name__ == '__main__':
    #args = parse_arguments()
    pmc_ids = ['PMC9169933', 'PMC9720135']
    html_dir = 'output'
    output_file = 'ebook.epub'
    #mock_args = argparse.Namespace(pmc_ids="your_pmc_ids_here",
    #                               output_file="your_output_file_here")

    main(pmc_ids, html_dir, output_file)
