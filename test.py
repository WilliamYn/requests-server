import xml.etree.ElementTree as ET
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

connect_str = 'DefaultEndpointsProtocol=https;AccountName=croppedfacesdataset;AccountKey=DTvc7Q8EQb0XBCUBiaWV/sWOnci1GbjfbMdhUhyzEFqL2EWDxtrZASnrkGfeL/QUyjiyrFF7b4/e+AStb3a86w==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = 'serverimages'
container_client = blob_service_client.get_container_client(container_name)

blobs = container_client.list_blobs()

for blob in blobs:
    if blob.name.endswith('/metadata.xml'):
    # if blob.name == '000_8WW2BH.jpg_bkfiles/metadata.xml':

        metadata_buffer = container_client.get_blob_client(blob.name).download_blob().readall()
        metadata_root = ET.fromstring(metadata_buffer)
        name = metadata_root.find("general").find("fileName")
        caption = metadata_root.find("mediaInfo").find("caption")
        ai_caption = metadata_root.find("mediaInfo").find("aiCaption")
        ai_generated_caption = metadata_root.find("mediaInfo").find("aiGeneratedCaption")
        # print(name.text, caption.text, ai_caption.text, '\n\n\n', ai_generated_caption.text)
        # if not ai_generated_caption:
        if ai_generated_caption is None:
            print(name.text, ai_generated_caption)


