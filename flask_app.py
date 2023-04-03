import io
from flask import Flask, request, send_file
import os
import xml.etree.ElementTree as ET
import json
from flask_cors import CORS
import requests

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

connect_str = 'DefaultEndpointsProtocol=https;AccountName=croppedfacesdataset;AccountKey=DTvc7Q8EQb0XBCUBiaWV/sWOnci1GbjfbMdhUhyzEFqL2EWDxtrZASnrkGfeL/QUyjiyrFF7b4/e+AStb3a86w==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = 'serverimages'
container_client = blob_service_client.get_container_client(container_name)

captionApiUrl = os.environ['captionApiUrl']
translateApiUrl = os.environ['translateApiUrl']
faceApiUrl = os.environ['faceApiUrl']
logoApiUrl = os.environ['logoApiUrl']

headers = {
    'Content-Type': 'application/json'
}

def get_files_from_azure():
    blobs = container_client.list_blobs()
    return blobs


def get_captions(blobs):
    captions = []

    for blob in blobs:
        if blob.name.endswith('/metadata.xml'):
            metadata_buffer = container_client.get_blob_client(blob.name).download_blob().readall()
            metadata_root = ET.fromstring(metadata_buffer)

            name = metadata_root.find("general").find("fileName")
            caption = metadata_root.find("mediaInfo").find("caption")
            ai_caption = metadata_root.find("mediaInfo").find("aiCaption")
            
            captions.append((name.text, str(caption.text), str(ai_caption.text)))
            
    return captions


def get_search_results(captions, search_value, search_type):
    images = []

    for img, normal_caption, ai_caption in captions:

        if search_value in normal_caption and 'normal' in search_type \
                or search_value in ai_caption and 'IA' in search_type:
            images.append((img, normal_caption, ai_caption))

    return images


app = Flask(__name__)
CORS(app)
captions = get_captions(get_files_from_azure())


@app.route('/')
def hello():
    return 'Hello World! -Server Service'


@app.route("/search", methods=["POST"])
def search():
    data = request.get_json()
    search_value = data["key"]
    search_type = data["type"]
    print(search_value, search_type)

    images = get_search_results(captions, search_value, search_type)

    return json.dumps(images, separators=(',', ':')), 200


@app.route('/image/<path:filename>')
def get_image(filename):
    print(filename)
    blob_client = container_client.get_blob_client(filename)
    image_buffer = blob_client.download_blob().readall()
    content_type = blob_client.get_blob_properties().content_settings.content_type
    return send_file(io.BytesIO(image_buffer), mimetype=content_type)


@app.route("/generate-label", methods=["GET", "POST"])
def handle_request():
    data = request.get_json()
    base64_str = data["image"]

    imagePayload = {"image": base64_str}

    captionResponse = requests.post(f"{captionApiUrl}/", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
    captionRes = captionResponse.json()
    print(captionRes)

    captionPayload = {'tags': captionRes["tags"], 'english_cap': captionRes["english_cap"]}
    translatedResponse = requests.post(f"{translateApiUrl}/", headers=headers, data=json.dumps(captionPayload), timeout=60, verify=False)
    translatedRes = translatedResponse.json()
    print(translatedRes)

    faceRes = ''
    try:
        faceResponse = requests.post(f"{faceApiUrl}/generate-face-label", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
        faceRes = faceResponse.json()
        print(faceRes)
    except:
        pass

    logoRes = ''
    try:
        logoResponse = requests.post(f"{logoApiUrl}/generate-hockey-team-label", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
        logoRes = logoResponse.json()
        print(logoRes)
    except:
        pass

    return json.dumps({'captionRes': captionRes, 'translatedRes': translatedRes,  'faceRes': faceRes, 'logoRes': logoRes})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
