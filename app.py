from datetime import datetime

from flask import Flask, request, render_template
import requests
import json

app = Flask(__name__)


@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        author = request.form['author']
        book = request.form['book']

        author = author.strip().replace(' ', '%20')

        url = f'https://openlibrary.org/search.json?author={author}&sort=new'
        response = requests.get(url)

        data = response.json()
        print(f"{response.json()}\n---- response done ----\n")

        # Check if the provided book name exists in the author's books
        author_key = ""
        for doc in data['docs']:
            if book.lower() in doc.get('title', '').lower():
                author_key = doc.get('author_key')[0]
                print(book.lower(), author_key)
                break
        if author_key != "":
            books = []
            for doc in data['docs']:
                # Filter the books for the matching author key
                if (author_key in doc.get('author_key', []) and
                        doc.get('type', []) == "work" and
                        (datetime.now().year - 15) <=
                        doc.get('first_publish_year', 15) <=
                        datetime.now().year):
                    books.append({
                        'title': doc.get('title', ''),
                        'first_publish_year': doc.get('first_publish_year', '')
                    })
            books = sorted(books, key=lambda k: k['first_publish_year'], reverse=True)
            #print(books)
            return render_template('results.html', books=books)
        else:
            return "Book not found for this author"

    return render_template('search.html')


if __name__ == "__main__":
    app.run(debug=True)
