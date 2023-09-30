from ebooklib import epub
import glob

if __name__ == '__main__':
    html_dir = 'output'
    book = epub.EpubBook()

    # set metadata
    book.set_identifier("id123456")
    book.set_title("Sample book")
    book.set_language("en")

    book.add_author("Author Authorowski")
    book.add_author(
        "Danko Bananko",
        file_as="Gospodin Danko Bananko",
        role="ill",
        uid="coauthor",
    )

    with open(f'{html_dir}/output.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
        
    # create chapter
    c1 = epub.EpubHtml(title="Intro", file_name="chap_01.xhtml", lang="hr")
    c1.content = (html_content)


    fig_files = glob.glob(f"{html_dir}/figs/*.jpg", recursive=True)
    print(fig_files)
    for fn in fig_files:
        #with open(fn, "rb") as reader:
        #    image_content = reader.read()
        #if True:
        #    image_content = open(fn, 'rb').read()
        #    img = epub.EpubImage(
        #        uid = f"{fn.split('.')[0]}",
        #        file_name = f"figs/{fn}",
        #        media_type = "image/jpg",
        #        content = image_content,
        #    )
        with open(fn, "rb") as reader:
            image_content = reader.read()
            ei = epub.EpubImage()
            ei.file_name = f"figs/{fn.split('/')[-1]}"
            ei.media_type = 'image/jpg'
            ei.content = image_content 
            book.add_item(ei)

    # add chapter
    book.add_item(c1)
    # add image
    #book.add_item(img)

    # define Table Of Contents
    book.toc = (
        epub.Link("chap_01.xhtml", "Introduction", "intro"),
        (epub.Section("Simple book"), (c1,)),
    )

    # add default NCX and Nav file
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())

    # define CSS style
    style = "BODY {color: white;}"
    nav_css = epub.EpubItem(
        uid="style_nav",
        file_name="style/nav.css",
        media_type="text/css",
        content=style,
    )

    # add CSS file
    book.add_item(nav_css)

    # basic spine
    book.spine = ["nav", c1]

    # write to the file
    epub.write_epub("test.epub", book)