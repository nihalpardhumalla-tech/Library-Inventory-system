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


# Initialize data when the server starts
media_database = load_media()


# -------------------------------------------------------
# API Endpoints
# -------------------------------------------------------

@app.route("/media", methods=["GET"])
def get_all_media():
    """1. List all available items."""
    return jsonify(media_database)


@app.route("/media/category/<string:category>", methods=["GET"])
def get_media_by_category(category):
    """2. List items by category."""
    filtered = {
        key: value 
        for key, value in media_database.items() 
        if value["category"].lower() == category.lower()
    }
    return jsonify(filtered)


@app.route("/media/search/<string:name>", methods=["GET"])
def search_media(name):
    """3. Search for exact name."""
    for key, value in media_database.items():
        if value["name"].lower() == name.lower():
            return jsonify({key: value})
    return jsonify({"error": "Media not found"}), 404


@app.route("/media/details/<string:item_id>", methods=["GET"])
def get_media_details(item_id):
    """4. Get metadata of a specific media item."""
    if item_id in media_database:
        return jsonify(media_database[item_id])
    return jsonify({"error": "Item not found"}), 404


@app.route("/media/create", methods=["POST"])
def create_media():
    """5. Create a new media item."""
    data = request.json

    required_fields = ["name", "author", "publication_date", "category"]
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing field: {field}"}), 400

    # Create unique ID
    item_id = str(len(media_database) + 1)

    media_database[item_id] = {
        "name": data["name"],
        "author": data["author"],
        "publication_date": data["publication_date"],
        "category": data["category"]
    }

    save_media(media_database)

    return jsonify({"message": "Media created", "id": item_id}), 201


@app.route("/media/delete/<string:item_id>", methods=["DELETE"])
def delete_media(item_id):
    """6. Delete a media item by ID."""
    if item_id not in media_database:
        return jsonify({"error": "Item not found"}), 404

    del media_database[item_id]

    save_media(media_database)

    return jsonify({"message": "Item deleted"}), 200


# -------------------------------------------------------
# Start the server
# -------------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
