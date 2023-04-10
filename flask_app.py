import io
from flask import Flask, request, send_file
import os
import xml.etree.ElementTree as ET
import json
from flask_cors import CORS
import requests
import base64

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

connect_str = 'DefaultEndpointsProtocol=https;AccountName=croppedfacesdataset;AccountKey=DTvc7Q8EQb0XBCUBiaWV/sWOnci1GbjfbMdhUhyzEFqL2EWDxtrZASnrkGfeL/QUyjiyrFF7b4/e+AStb3a86w==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = 'serverimages'
container_client = blob_service_client.get_container_client(container_name)

# captionApiUrl = os.environ['captionApiUrl']
# translateApiUrl = os.environ['translateApiUrl']
# faceApiUrl = os.environ['faceApiUrl']
# logoApiUrl = os.environ['logoApiUrl']
captionApiUrl = "http://image-caption.eastus.cloudapp.azure.com:3000"
translateApiUrl = "https://translate-app.wittyriver-06391a5d.eastus.azurecontainerapps.io"
faceApiUrl = "https://facerecon-app.wittyriver-06391a5d.eastus.azurecontainerapps.io"
logoApiUrl = "https://logo-app.wittyriver-06391a5d.eastus.azurecontainerapps.io"

print('========= API URLS =========')
print(captionApiUrl)
print(translateApiUrl)
print(faceApiUrl)
print(logoApiUrl)
print('============================')

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
            ai_generated_caption = metadata_root.find("mediaInfo").find("aiGeneratedCaption")

            if ai_generated_caption is not None:
                captions.append((name.text, str(caption.text), str(ai_generated_caption.text)))
            else:
                print(name.text)

    return captions


def get_search_results(captions, search_value, search_type):
    images = []

    for img, normal_caption, ai_caption in captions:

        if search_value in normal_caption and 'normal' in search_type \
                or search_value in ai_caption and 'IA' in search_type:
            images.append((img, normal_caption, ai_caption))

    return images


def build_caption_dict(caption_dict, container_name):
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()

    for i, blob in enumerate(blobs):
        if not blob.name.endswith('.xml'):
            print(blob.name)
            
            # Get image base64 of current blob
            blob_contents  = container_client.get_blob_client(blob.name).download_blob().content_as_bytes()
            base64_str = base64.b64encode(blob_contents).decode('utf-8')

            try:
                # Generate caption
                captionRes, translatedRes, faceRes, logoRes = caption_image(base64_str)
                caption_dict[blob.name] = format_caption_element(captionRes, translatedRes, faceRes, logoRes)
                print('caption:', caption_dict[blob.name])
            except:
                pass


def update_xml_files(caption_dict, container_name):
    container_client = blob_service_client.get_container_client(container_name)
    blobs = container_client.list_blobs()
    for i, blob in enumerate(blobs):
        print(blob.name)
        image_name = blob.name.replace('_bkfiles/metadata.xml', '')

        if blob.name.endswith('/metadata.xml') and image_name in caption_dict:
            # Get caption
            caption_element = caption_dict[image_name]

            # Update metadata blob
            blob_client = container_client.get_blob_client(blob.name)
            metadata_content = blob_client.download_blob().readall()
            metadata_content_str = metadata_content.decode('utf-8')
            metadata_content_str = metadata_content_str.replace('</mediaInfo>', caption_element + '</mediaInfo>')
            metadata_content_bytes = metadata_content_str.encode('utf-8')

             # Upload the updated metadata blob
            blob_client.upload_blob(metadata_content_bytes, overwrite=True)


def caption_images(container_name):
    caption_dict = {}
    
    build_caption_dict(caption_dict, container_name)

    update_xml_files(caption_dict, container_name)


def caption_image(base64_str):
    print('CAPTION_IMAGE')
    captionRes, translatedRes, faceRes, logoRes = {}, {}, '', ''

    try:
        imagePayload = {"image": base64_str}
        captionResponse = requests.post(f"{captionApiUrl}/", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
        captionRes = captionResponse.json()
        print(captionRes)

        captionPayload = {'tags': captionRes["tags"], 'english_cap': captionRes["english_cap"]}
        translatedResponse = requests.post(f"{translateApiUrl}/", headers=headers, data=json.dumps(captionPayload), timeout=60, verify=False)
        translatedRes = translatedResponse.json()
        print(translatedRes)

        faceResponse = requests.post(f"{faceApiUrl}/generate-face-label", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
        faceRes = faceResponse.json()
        print(faceRes)

        logoResponse = requests.post(f"{logoApiUrl}/generate-hockey-team-label/", headers=headers, data=json.dumps(imagePayload), timeout=60, verify=False)
        logoRes = logoResponse.json()
        print(logoRes)
    except:
        pass

    return captionRes, translatedRes, faceRes, logoRes


def format_caption_element(captionRes, translatedRes, faceRes, logoRes):
    caption = '<aiGeneratedCaption>'

    # French generated caption
    caption += translatedRes['captions'][len(translatedRes['captions']) - 1][1] + ' '

    # English generated caption
    caption += translatedRes['captions'][len(translatedRes['captions']) - 1][0] + ' '

    # Tags
    for tag in translatedRes['tags']:
        if float(tag[1]) > 0.01:
            caption += tag[2][0] + ' '

    # Face prediction
    if faceRes['prediction']:
        caption += faceRes['prediction'] + ' '

    # Logo prediction
    if logoRes and logoRes['prediction']:
        caption += logoRes['prediction'] + ' '

    caption += '</aiGeneratedCaption>'

    return caption

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


@app.route("/caption-single-image", methods=["GET", "POST"])
def handle_caption_single_image():
    data = request.get_json()
    base64_str = data["image"]

    captionRes, translatedRes, faceRes, logoRes = caption_image(base64_str)

    return json.dumps({'captionRes': captionRes, 'translatedRes': translatedRes,  'faceRes': faceRes, 'logoRes': logoRes})


@app.route("/caption-images", methods=["GET", "POST"])
def handle_caption_images():
    print('CAPTION IMAGES')
    data = request.get_json()
    container_name = data["container_name"]

    caption_images(container_name)

    return json.dumps({'status': 'success'})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0')
