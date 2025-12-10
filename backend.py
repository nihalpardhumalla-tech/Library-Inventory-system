from flask import Flask, request, jsonify
import json
import os

app = Flask(__name__)

DATA_FILE = "media.json"


# -------------------------------------------------------
# Helper functions: load & save data
# -------------------------------------------------------

def load_media():
    """Load media dictionary from JSON file."""
    if not os.path.exists(DATA_FILE):
        return {}

    with open(DATA_FILE, "r") as file:
        return json.load(file)


def save_media(media_dict):
    """Save media dictionary to JSON file."""
    with open(DATA_FILE, "w") as file:
        json.dump(media_dict, file, indent=4)


# Note: load_media() will be called inside each endpoint so the server
# always reads the current `media.json` file without needing a restart.


# -------------------------------------------------------
# API Endpoints
# -------------------------------------------------------

@app.route("/media", methods=["GET"])
def get_all_media():
    """1. List all available items."""
    return jsonify(load_media())


@app.route("/media/category/<string:category>", methods=["GET"])
def get_media_by_category(category):
    """2. List items by category."""
    media = load_media()
    filtered = {
        key: value
        for key, value in media.items()
        if str(value.get("category", "")).lower() == category.lower()
    }
    return jsonify(filtered)


@app.route("/media/search/<string:name>", methods=["GET"])
def search_media(name):
    """3. Search for exact name."""
    media = load_media()
    for key, value in media.items():
        if str(value.get("name", "")).lower() == name.lower():
            return jsonify({key: value})
    return jsonify({"error": "Media not found"}), 404


@app.route("/media/details/<string:item_id>", methods=["GET"])
def get_media_details(item_id):
    """4. Get metadata of a specific media item."""
    media = load_media()
    if item_id in media:
        return jsonify(media[item_id])
    return jsonify({"error": "Item not found"}), 404


@app.route("/media/create", methods=["POST"])
def create_media():
    """5. Create a new media item."""
    import uuid
    data = request.json or {}

    required_fields = ["name", "author", "publication_date", "category"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    media = load_media()
    # Create unique UUID
    item_id = str(uuid.uuid4())

    media[item_id] = {
        "name": data["name"],
        "author": data["author"],
        "publication_date": data["publication_date"],
        "category": data["category"]
    }

    save_media(media)

    return jsonify({"message": "Media created", "id": item_id}), 201


@app.route("/media/delete/<string:item_id>", methods=["DELETE"])
def delete_media(item_id):
    """6. Delete a media item by ID."""
    media = load_media()
    if item_id not in media:
        return jsonify({"error": "Item not found"}), 404

    del media[item_id]
    save_media(media)

    return jsonify({"message": "Item deleted"}), 200


# -------------------------------------------------------
# Start the server
# -------------------------------------------------------
if __name__ == "__main__":
    # Populate database with sample data
    import uuid
    
    sample_data = {}
    
    # 20 Books
    books = [
        ("The Great Gatsby", "F. Scott Fitzgerald", "1925"),
        ("To Kill a Mockingbird", "Harper Lee", "1960"),
        ("Pride and Prejudice", "Jane Austen", "1813"),
        ("The Catcher in the Rye", "J.D. Salinger", "1951"),
        ("1984", "George Orwell", "1949"),
        ("Brave New World", "Aldous Huxley", "1932"),
        ("The Hobbit", "J.R.R. Tolkien", "1937"),
        ("The Lord of the Rings", "J.R.R. Tolkien", "1954"),
        ("Moby Dick", "Herman Melville", "1851"),
        ("War and Peace", "Leo Tolstoy", "1869"),
        ("Crime and Punishment", "Fyodor Dostoevsky", "1866"),
        ("The Brothers Karamazov", "Fyodor Dostoevsky", "1879"),
        ("Jane Eyre", "Charlotte Brontë", "1847"),
        ("Wuthering Heights", "Emily Brontë", "1847"),
        ("The Odyssey", "Homer", "800 BC"),
        ("The Iliad", "Homer", "800 BC"),
        ("Don Quixote", "Miguel de Cervantes", "1605"),
        ("Les Misérables", "Victor Hugo", "1862"),
        ("The Hunchback of Notre-Dame", "Victor Hugo", "1831"),
        ("Frankenstein", "Mary Shelley", "1818"),
    ]
    
    for title, author, year in books:
        sample_data[str(uuid.uuid4())] = {
            "name": title,
            "author": author,
            "publication_date": year,
            "category": "Book"
        }
    
    # 20 Magazines
    magazines = [
        ("National Geographic", "National Geographic Society", "2024"),
        ("Time", "Time Inc.", "2024"),
        ("The Economist", "The Economist Newspaper", "2024"),
        ("Scientific American", "Springer Nature", "2024"),
        ("Nature", "Springer Nature", "2024"),
        ("Science", "American Association for the Advancement of Science", "2024"),
        ("Wired", "Condé Nast", "2024"),
        ("Popular Mechanics", "Hearst Communications", "2024"),
        ("Smithsonian", "Smithsonian Institution", "2024"),
        ("Vogue", "Condé Nast", "2024"),
        ("GQ", "Condé Nast", "2024"),
        ("Vanity Fair", "Condé Nast", "2024"),
        ("Forbes", "Forbes", "2024"),
        ("Business Week", "Bloomberg", "2024"),
        ("The New Yorker", "Condé Nast", "2024"),
        ("Reader's Digest", "Trusted Media", "2024"),
        ("Cosmopolitan", "Hearst Communications", "2024"),
        ("People", "Time Inc.", "2024"),
        ("Entertainment Weekly", "Time Inc.", "2024"),
        ("Sports Illustrated", "Time Inc.", "2024"),
    ]
    
    for title, publisher, year in magazines:
        sample_data[str(uuid.uuid4())] = {
            "name": title,
            "author": publisher,
            "publication_date": year,
            "category": "Magazine"
        }
    
    save_media(sample_data)
    app.run(debug=True)
