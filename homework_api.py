
import os
import json
import requests


ACCESS_TOKEN = ''
USER_ID = int(input("Enter UserID: ")) 
TOKEN_YD = input("Enter TokenYandexDisk: ")
UPLOAD_URL = 'https://cloud-api.yandex.net/v1/disk/resources/upload'
FOLDER_PATH = 'HW_Netology'


class VkApiClient:
    api_base_url = 'https://api.vk.com/method/'

    def __init__(self, access_token, user_id):
        self.access_token = access_token
        self.user_id = user_id

    def get_common_params(self):
        return {
            'access_token': self.access_token,
            'v': '5.199'
        }
    
    def _build_url(self, api_method):
        return f'{self.api_base_url}{api_method}'
    
    def get_profile_photos(self):
            params = self.get_common_params()
            params.update({'owner_id': self.user_id, 'album_id': 'profile'})
            response = requests.get(self._build_url('photos.get'), params=params)
            return response.json()  

    def get_likes_list_photo(self, count=5):
        params = self.get_common_params()
        photos = self.get_profile_photos().get('response', {}).get('items', [])[-count:]
        likes_list = []     

        for photo in photos:
            id_photo = photo['id']            
            params.update({'owner_id': self.user_id, 'type': 'photo', 'item_id': id_photo})
            response = requests.get(self._build_url('likes.getList'), params=params).json()['response']['count']
            likes_list.append(response)

        print(f"Likes received: {len(likes_list)}") 
        return likes_list 

    def get_photos_urls(self, count=5):
        response = self.get_profile_photos()
        photos = response.get('response', {}).get('items', [])[-count:]
        max_size_photos_urls = []

        for photo in photos:
            max_size_photo_url = None
            max_res = 0
            for photo_size in photo.get('sizes', []):
                res = photo_size.get('height', 0) * photo_size.get('width', 0)
                if res > max_res:
                    max_res = res
                    max_size_photo_url = photo_size['url']                       
            max_size_photos_urls.append(max_size_photo_url)

        print(f"URLs received: {len(max_size_photos_urls)}")        
        return max_size_photos_urls
    
    def create_folder_YD(self):
        url_create_folder = 'https://cloud-api.yandex.net/v1/disk/resources'
        headers = {'Authorization': TOKEN_YD}
        params = {'path': FOLDER_PATH}

        response = requests.get(url_create_folder, headers=headers, params=params)

        if response.status_code == 200:
            print('Folder is exist')
            return
        else:
            requests.put(url_create_folder, headers=headers, params=params)
            print('Folder created')
    
    def dict_likes_photos(self):
        dict_ = dict(zip(self.get_photos_urls(), self.get_likes_list_photo()))
        return dict_ 
    
    def upload_images_YD(self):
        self.create_folder_YD()
        file_in_folder = self.get_info_files_in_folder()
        uploaded_files_info = []

        for key, value in self.dict_likes_photos().items():
            print(key, value)
            if key is not None:             
                headers = {
                    'Authorization': TOKEN_YD
                    }
                params = {
                    'path': f'{FOLDER_PATH}/{value}.jpg'
                    }
                response = requests.get(UPLOAD_URL, 
                                        headers=headers, 
                                        params=params) 
                if f"{value}.jpg" in file_in_folder:                                    
                    print(f"This file ({value}.jpg) has already been downloaded")

                else:
                    try:
                        url_for_upload = response.json()['href'] 
                        photo_data = requests.get(key).content                        
                        with open(f"{value}.jpg", 'wb') as f:
                            f.write(photo_data)
                        file_size = os.path.getsize(f"{value}.jpg")

                        with open(f"{value}.jpg", 'rb') as f:
                            requests.put(url_for_upload, files={'file': f})   
                        print(f"Photo ({value}.jpg) is being uploaded using the link: {url_for_upload}")                     
                        uploaded_files_info.append({"file_name": f"{value}.jpg", "size": file_size})

                    except KeyError:
                        print(f"Failed to upload photo ({value}.jpg) due to an error: {response.json()['error']}")
            else:
                print(f'URL is None. Link = {key}, likes = {value}')

        with open("uploaded_files_info.json", "w") as file:
            json.dump(uploaded_files_info, file)

    def get_info_files_in_folder(self):
        headers = {
            'Authorization': TOKEN_YD
            }
        params = {
            'path': f'{FOLDER_PATH}/',
            'fields': '_embedded.items.path'
            }

        response = requests.get('https://cloud-api.yandex.net/v1/disk/resources/', 
                                        headers=headers, 
                                        params=params)  
        data = response.json()['_embedded']['items']
        file_names = [item['path'].split('/')[-1] for item in data]

        return file_names


if __name__ == '__main__':
    vk_client = VkApiClient(ACCESS_TOKEN, USER_ID)
    vk_client.upload_images_YD()
