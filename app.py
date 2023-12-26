import os

from flask_bootstrap import Bootstrap
from datetime import datetime
from PIL import Image
from flask import Flask, request, render_template, redirect
from pkgs.exclusions import excluded_books
import requests

app = Flask(__name__)
Bootstrap(app)


@app.route('/', methods=['GET', 'POST'])
@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        author = request.form['author']
        book = request.form['book']

        author = {
            "raw": author.strip(),
            "for_url": author.strip().replace(' ', '%20'),
            "fl_cap": author.strip().title(),
            "standardized": format_string(author.strip()),
            "key": "",
            "image": ""
        }

        download_directory = "downloaded_images"

        baseurl = 'https://openlibrary.org'
        author_url = f'{baseurl}/search.json?author={author["for_url"]}&sort=new'
        response = requests.get(author_url)

        data = response.json()
        # print(f"{response.json()}\n---- response done ----\n")

        # Check if the provided book name exists in the author's books
        author_key = ""
        for doc in data['docs']:
            if book.lower() in doc.get('title', '').lower():
                author["key"] = doc.get('author_key')[0]
                # print(book.lower(), author_key)
                break

        if author["key"] != "":
            # found_author_image = False
            books = []

            for doc in data['docs']:
                # print(f"{author['key']} - {doc.get('title', '')}")

                if {"author_key": author['key'], "title": doc.get('title', '')} in excluded_books:
                    continue

                # Filter the books for the matching author key
                if (author["key"] in doc.get('author_key', []) and
                        (author["fl_cap"] in doc.get('author_name', [])) and
                        doc.get('type', []) == "work" and
                        (datetime.now().year - 15) <=
                        doc.get('first_publish_year', 15) <=
                        datetime.now().year):

                    isbn = doc.get('isbn', [''])[0]
                    asin = doc.get('asin', [''])[0]

                    identifier_type = 'isbn'
                    identifier = isbn
                    if isbn == '':
                        identifier_type = 'asin'
                        identifier = asin

                    book_cover_image = ""
                    title_compressed = format_string(doc.get('title', ''))

                    if not os.path.exists(f'./static/{download_directory}'):
                        os.makedirs(f'./static/{download_directory}')

                    # do we have an author pic?
                    author_image_name = (f'{download_directory}/{author["standardized"]}'
                                         f'-M.jpg')
                    if not os.path.exists(f'./static/{author_image_name}'):
                        url = f'https://covers.openlibrary.org/a/{identifier_type}/{identifier}-M.jpg'
                        download_and_save(url, author_image_name)

                        if os.path.exists(f'./static/{author_image_name}'):
                            author["image"] = author_image_name

                    downloaded_image_name = (
                        f'{download_directory}/{author["standardized"]}'
                        f'-{title_compressed}-{identifier_type}-{identifier}'
                        f'-M.jpg')

                    if not os.path.exists(f'./static/{downloaded_image_name}'):
                        url = f'https://covers.openlibrary.org/b/{identifier_type}/{identifier}-M.jpg'
                        download_and_save(url, downloaded_image_name)
                    else:
                        book_cover_image = downloaded_image_name

                    books.append({
                        'title': doc.get('title', ''),
                        'first_publish_year': doc.get('first_publish_year', ''),
                        'isbn': isbn,
                        'asin': asin,
                        'book_cover_image': book_cover_image
                    })
            books = sorted(books, key=lambda k: k['first_publish_year'], reverse=True)
            # print(books)
            # print(author["image"])
            return render_template('results.html',
                                   author=author,
                                   books=books)
        else:
            return "Book not found for this author"

    return render_template('search.html')

@app.route('/image_upload', methods=['GET'])
def display_upload_form():
    return render_template('image_upload.html')


@app.route('/image_upload', methods=['POST'])
def handle_image_upload():
    if 'file' not in request.files:
        return "No 'file' key in request.files"

    file = request.files['file']
    file_array = file.filename.split('.')


    # Note: The convert() function is used to remove alpha channel
    # (transparency).
    # You should only use it if you're sure you're not handling
    # transparent images. In this case we are expecting jpg images.
    img = Image.open(file.stream).convert('RGB')
    px2size = {800: "_large",
               256: "_medium",
               128:  "_small"}
    sizes = [(800, 800),
             (256, 256),
             (128, 128)]

    # Check if folder exists and create one if it doesn't
    output_folder_path = 'static/resized_images'
    if not os.path.exists(output_folder_path):
        os.makedirs(output_folder_path)

    for size in sizes:
        img_copy = img.copy()
        img_copy.thumbnail(size)


        output_filename = f'{file_array[0]}{px2size[size[0]]}.{file_array[1]}'
        # Save the resized image
        img_copy.save(os.path.join(output_folder_path,
                                   output_filename))

    return redirect('/image_upload')


def format_string(source_string):
    return source_string.title().replace(" ", "")


def download_and_save(url, filename):
    outfile = f'./static/{filename}'
    if url.startswith('http'):
        response = requests.get(url, stream=True)
        response.raise_for_status()

        with open(outfile, 'wb') as out_file:
            out_file.write(response.content)

        try:
            with Image.open(outfile) as img:
                img.verify()  # verify that it is, in fact, an image
                if img.size == (1, 1):
                    # print('Image is a 1x1 GIF:', outfile)
                    os.remove(outfile)
        except (IOError, SyntaxError) as e:
            print('Bad file:', outfile)
            os.remove(outfile)


if __name__ == "__main__":
    app.run(debug=True)
