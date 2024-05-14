import configparser
import requests
from datetime import datetime
import json
from tqdm import tqdm


class VkApiClient:
    api_base_url = 'https://api.vk.com/method/'

    def __init__(self, access_token, user_id, cnt_dwnload_photo=5):
        self.access_token = access_token
        self.user_id = user_id
        self.cnt_dwnload_photo = cnt_dwnload_photo

    def _get_common_params(self):
        return {
            'access_token': self.access_token,
            'v': '5.199'
            } 

    def _convert_screen_name_to_id(self):        
        '''The method belongs to the VkApiClient class. The method handles the situation when the user enters the user's screen_name instead of the user ID. 
        The method calls endopintusers.get to obtain information about the user and, if the screen_name matches, then returns the user ID. 
        If the user enters an ID, the method does not compare anything and returns the ID'''

        if self.user_id.isdigit():
            return self.user_id
        else:
            params = self._get_common_params()
            params.update({'user_ids': self.user_id, "fields":'screen_name'})

            response = requests.get(self._build_url('users.get'), params=params).json()

            if 'response' in response:
                return response['response'][0]['id']
            else:
                return self.user_id   

    def _build_url(self, api_method):
        return f'{self.api_base_url}{api_method}'
    
    def get_profile_photos(self):
        '''The method belongs to the VkApiClient class. The method allows you to obtain information about the profile photos of the specified user. 
        The count parameter allows you to specify the number of photos about which you want to find out information'''

        params = self._get_common_params()
        count = self.cnt_dwnload_photo
        user_id = self._convert_screen_name_to_id()        
        params.update({'owner_id': user_id, 'album_id': 'profile', 'extended': 'likes', "photo_sizes": '1'})

        response = requests.get(self._build_url('photos.get'), params=params).json()

        return response.get('response', {}).get('items', [])[0:count]

    def get_photo_url_likes(self):
        '''The method belongs to the VkApiClient class. The method determines the photo with the maximum resolution and adds it to the list. 
        If one of the parameters (height and/or width) is zero, then the method selects the photo and returns the last URL from the parameters 
        (the last URL is a link to a copy of the photo with the highest resolution)'''

        photos = self.get_profile_photos()
        max_size_photos_urls = []
        for photo in photos:
            max_size_photo_url = max(photo.get('sizes', []), key=lambda x: x.get('height', 0) * x.get('width', 0))
            if max_size_photo_url['height'] or max_size_photo_url['width'] == 0:
                max_size_photos_urls.append((photo['sizes'][-1]['url'], photo['likes']['count']))
                continue
            max_size_photos_urls.append((max_size_photo_url['url'], photo['likes']['count']))

        return max_size_photos_urls  
 

class YDApi:        
    yandex_api = 'https://cloud-api.yandex.net/v1/disk/resources'
    folder_path = 'HW_Netology'

    def __init__(self, token_yd):
        self.token_yd = token_yd

    def create_folder_YD(self):
        '''The method belongs to the YDApi class. The method creates a directory with the specified name on the Yandex Disk resource. 
        If the directory exists, the method will return the message "Folder is exist. Status code"'''

        headers = {'Authorization': self.token_yd}
        params = {'path': self.folder_path}
        response = requests.put(self.yandex_api, headers=headers, params=params)

        if response.status_code == 200:
            print('Folder created')
        else:
            print(f'Folder is exist. Status code = {response.status_code}')

    def get_info_files_in_folder(self):
        '''The method belongs to the YDApi class. The method checks for the presence of files in the specified directory and returns a list of files, 
        or an empty list if there are no files'''

        headers = {'Authorization': self.token_yd}
        params = {'path': f'{self.folder_path}/', 'fields': '_embedded.items.path'}
        response = requests.get(self.yandex_api, headers=headers, params=params)
        data = response.json().get('_embedded', {}).get('items', [])
        file_names = [item['path'].split('/')[-1] for item in data]

        return file_names

    def _check_file_name(self, file_in_folder, file_name, photo_likes):
        '''The method belongs to the YDApi class. The method checks whether a file with the same name exists in the specified directory. 
        If exists, the current date will be added to the new file name. If there is no file with a similar name, 
        then the file name does not change and is equal to the number of likes under the specified photo'''

        if file_name in file_in_folder: 
                timestamp = datetime.now().strftime('%Y%m%d%H%M%S')                               
                print(f"A file with the same name ({file_name}) already been downloaded. The current date ({timestamp}) will be appended to the file name")
                file_name = f"{photo_likes}_{timestamp}.jpg"
                response = requests.get(f"{self.yandex_api}/upload", headers={'Authorization': self.token_yd}, params={'path': f'{self.folder_path}/{file_name}', 'overwrite':'true'})
                return response
        else:
            response = requests.get(f"{self.yandex_api}/upload", headers={'Authorization': self.token_yd}, params={'path': f'{self.folder_path}/{file_name}', 'overwrite':'true'})
            return response
    
    def upload_images_YD(self, vk_client): 
        '''The method belongs to the YDApi class. Method uploads photos to Yandex Disk'''

        self.create_folder_YD()      
        file_in_folder = self.get_info_files_in_folder()
        print(f"Files in the folder: {file_in_folder}")        

        for photo_url, photo_likes in tqdm(vk_client.get_photo_url_likes()):                     
            file_name = f"{photo_likes}.jpg"
            response_get_url_for_upload = self._check_file_name(file_in_folder=file_in_folder, file_name=file_name, photo_likes=photo_likes)
         
            if 'href' in response_get_url_for_upload.json():
                url_for_upload = response_get_url_for_upload.json()['href']                
                photo_data = requests.get(photo_url).content
                response_upload_file = requests.put(url_for_upload, data=photo_data)

                if response_upload_file.status_code in (200, 201, 202):
                    print(f"Photo ({file_name}) is being uploaded using the link: {url_for_upload}")                   
                else:
                    print(f"Photo {file_name} not uploaded. Status code = {response_upload_file.status_code}")
            else:
                print(f"Failed to upload photo ({file_name}) due to an error: {response_get_url_for_upload.json().get('error')}")   

        write_to_file_name_size(self.yandex_api, self.token_yd, self.folder_path) 


def write_to_file_name_size(url_yandex, token_yd, folder_path):
    uploaded_files_info = []
    data = requests.get(url_yandex, headers={'Authorization': token_yd}, params={'path': folder_path}).json().get('_embedded', {}).get('items', [])

    for item in data:
        if 'size' in item:
            file_info = {
                "file_name": item['name'],
                "size": item['size']
                }
            uploaded_files_info.append(file_info) 

    with open("uploaded_files_info.json", "w") as file_out:
        json.dump(uploaded_files_info, file_out, indent=1)  
        

if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('settings.ini')

    vk_client = VkApiClient(
        config["VK"]["access_token"], 
        user_id='pavel_inkin', 
        cnt_dwnload_photo=2)  

    yd_client = YDApi(config["YD"]["token_yd"])
    yd_client.upload_images_YD(vk_client)
