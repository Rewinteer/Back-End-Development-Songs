from . import app
import os
import json
import pymongo
from flask import jsonify, request, make_response, abort, url_for  # noqa; F401
from pymongo import MongoClient
from bson import json_util
from pymongo.errors import OperationFailure
from pymongo.results import InsertOneResult
from bson.objectid import ObjectId
import sys

SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
json_url = os.path.join(SITE_ROOT, "data", "songs.json")
songs_list: list = json.load(open(json_url))

# client = MongoClient(
#     f"mongodb://{app.config['MONGO_USERNAME']}:{app.config['MONGO_PASSWORD']}@localhost")
mongodb_service = os.environ.get('MONGODB_SERVICE')
mongodb_username = os.environ.get('MONGODB_USERNAME')
mongodb_password = os.environ.get('MONGODB_PASSWORD')
mongodb_port = os.environ.get('MONGODB_PORT')

print(f'The value of MONGODB_SERVICE is: {mongodb_service}')

if mongodb_service == None:
    app.logger.error('Missing MongoDB server in the MONGODB_SERVICE variable')
    # abort(500, 'Missing MongoDB server in the MONGODB_SERVICE variable')
    sys.exit(1)

if mongodb_username and mongodb_password:
    url = f"mongodb://{mongodb_username}:{mongodb_password}@{mongodb_service}"
else:
    url = f"mongodb://{mongodb_service}"


print(f"connecting to url: {url}")

try:
    client = MongoClient(url)
except OperationFailure as e:
    app.logger.error(f"Authentication error: {str(e)}")

db = client.songs
db.songs.drop()
db.songs.insert_many(songs_list)
songs_collection = db.songs

def parse_json(data):
    return json.loads(json_util.dumps(data))

######################################################################
# INSERT CODE HERE
######################################################################
@app.route("/health")
def health():
    return {"status": "OK"}, 200

@app.route("/count")
def count():
    songs_count = songs_collection.count_documents({})
    return {"count": songs_count}, 200

@app.route("/song")
def songs():
    songs = parse_json(songs_collection.find({}))
    return {"songs": songs}, 200

@app.route("/song/<int:id>")
def get_song_by_id(id):
    song = parse_json(songs_collection.find_one({"id": id}))
    if song:
        return jsonify(song), 200
    return {"message": f"song with id {id} not found"}, 404

@app.route("/song", methods=["POST"])
def create_song():
    new_song = request.get_json()
    songs = songs_collection.find({})
    for song in songs:
        if new_song['id'] == song['id']:
            return {"Message": f"song with id {song['id']} already present"}, 302
    
    ins_id = str(songs_collection.insert_one(new_song).inserted_id)
    
    return {"inserted id":{"$oid": ins_id}}, 201

@app.route("/song/<int:id>", methods=["PUT"])
def update_song(id):
    song = parse_json(songs_collection.find_one({"id": id}))
    if song:
        new_data = {"$set": request.get_json()}
        update = songs_collection.update_one({"id": id}, new_data)

        if update.raw_result["nModified"] == 0:   
            return {"message":"song found, but nothing updated"}, 200
        
        song = parse_json(songs_collection.find_one({"id": id}))
        return jsonify(song), 200
    
    return {"message": f"song with id {id} not found"}, 404

@app.route("/song/<int:id>", methods=["DELETE"])
def delete_song(id):
    deletion = songs_collection.delete_one({"id": id})
    if deletion.deleted_count == 1:
        return ({}, 204)
    return {"message": "song not found"}, 404