from flask import Flask, jsonify, request
import argparse

app = Flask(__name__)

# In-memory media store; each item is a dict with an 'id'
_media = [
    {"id": 1, "name": "The Hobbit", "author": "J.R.R. Tolkien", "publication_date": "1937", "category": "Book"},
    {"id": 2, "name": "Inception", "author": "Christopher Nolan", "publication_date": "2010", "category": "Film"},
    {"id": 3, "name": "National Geographic", "author": "Various", "publication_date": "2020-06", "category": "Magazine"},
]
_next_id = 4


@app.route('/media', methods=['GET'])
def get_media():
    # Return as a list to exercise frontend normalization logic
    return jsonify(list(_media))


@app.route('/media/category/<category>', methods=['GET'])
def get_by_category(category):
    filtered = [m for m in _media if str(m.get('category', '')).lower() == category.lower()]
    return jsonify(filtered)


@app.route('/media/search/<name>', methods=['GET'])
def search(name):
    s = name.lower()
    filtered = [m for m in _media if s in str(m.get('name', '')).lower()]
    return jsonify(filtered)


@app.route('/media/create', methods=['POST'])
def create():
    global _next_id
    payload = request.get_json() or {}
    name = payload.get('name')
    if not name:
        return jsonify({"error": "name required"}), 400
    item = {
        'id': _next_id,
        'name': name,
        'author': payload.get('author'),
        'publication_date': payload.get('publication_date'),
        'category': payload.get('category')
    }
    _media.append(item)
    _next_id += 1
    return jsonify(item)


@app.route('/media/delete/<int:item_id>', methods=['DELETE'])
def delete(item_id):
    global _media
    before = len(_media)
    _media = [m for m in _media if int(m.get('id')) != int(item_id)]
    if len(_media) == before:
        return jsonify({"error": "not found"}), 404
    return jsonify({"deleted": item_id})


def main():
    parser = argparse.ArgumentParser(description='Mock backend for frontend testing')
    parser.add_argument('--port', type=int, default=5001, help='Port to run the mock backend on')
    args = parser.parse_args()
    app.run(host='127.0.0.1', port=args.port)


if __name__ == '__main__':
    main()
