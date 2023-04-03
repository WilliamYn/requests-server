import os
from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient

connect_str = 'DefaultEndpointsProtocol=https;AccountName=croppedfacesdataset;AccountKey=DTvc7Q8EQb0XBCUBiaWV/sWOnci1GbjfbMdhUhyzEFqL2EWDxtrZASnrkGfeL/QUyjiyrFF7b4/e+AStb3a86w==;EndpointSuffix=core.windows.net'
blob_service_client = BlobServiceClient.from_connection_string(connect_str)
container_name = 'serverimages'
container_client = blob_service_client.get_container_client(container_name)

folder_path = '2021/01/2021-01-03/'

for i, filename in enumerate(os.listdir(folder_path)):
    file_folder_path = os.path.join(folder_path, filename)
    
    if os.path.isdir(file_folder_path):
        azure_subdirectory_name = f"{filename}/"
        
        for file in os.listdir(file_folder_path):
            blob_name = os.path.join(azure_subdirectory_name, file)
            blob_client = container_client.get_blob_client(blob=blob_name)
            local_file_path = os.path.join(file_folder_path, file)
            try:
                with open(local_file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
            except:
                print('wayr', local_file_path)
                continue

    else:
        blob_name = filename
        blob_client = container_client.get_blob_client(blob=blob_name)
        try:
            with open(file_folder_path, "rb") as data:
                blob_client.upload_blob(data, overwrite=True)
        except:
            print('wayr', file_folder_path)
            continue