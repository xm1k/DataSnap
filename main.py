api_key = 'To work you need API_KEY from Custom Search API'

import os
import requests
from PIL import Image
from io import BytesIO
from config import api_key
from tqdm import tqdm

cse_id = '431e5b8b2faec4801'

max_size = (-1,-1) # -1 if without restrictions on permission
target_size = (256,256)
target_format = 'JPEG'
crop_threshold = 0.5 # Acceptable image crop percentage
imgs_count = 0

skip_delay = 10 # Load wait time

user_agent = {
    'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
}

def get_img_links(prompt, links_count, api_key, cse_id, start):
    url = f"https://www.googleapis.com/customsearch/v1"
    params = {
        'q': prompt,
        'cx': cse_id,
        'searchType': 'image',
        'key': api_key,
        'num': links_count,
        'start': start
    }
    response  = requests.get(url, params=params)
    data = response.json()
    if 'items' in data:
        return [item['link'] for item in data['items']]
    else:
        return []

def check_img(size):
    if(size[0] < target_size[0] or size[1] < target_size[1]):
        return False
    if((size[0] > max_size[0] and max_size[0]!=-1) or (size[1] > max_size[1] and max_size[1]!=-1)):
        return False
    sides_ratio = target_size[0]/target_size[1]
    width, height = size
    crop = 0
    if width / height > sides_ratio:
        new_width = int(height * sides_ratio)
        crop = (new_width*height)/(width*height)
    else:
        new_height = int(width / sides_ratio)
        crop = (new_height * width) / (width * height)
    if(1-crop>crop_threshold):
        return False
    return True

def processing_img(img, target_size):
    width, height = img.size
    sides_ratio = target_size[0]/target_size[1]

    # Cropping

    if width/height > sides_ratio:
        new_width = int(height * sides_ratio)
        left = (width - new_width) / 2
        right = left + new_width
        img = img.crop((left, 0 , right, height))
    else:
        new_height = int(width / sides_ratio)
        top = height - new_height
        bot = top+new_height
        img = img.crop((0, top, width, bot))

    # Scaling

    img = img.resize(target_size)

    return img

def download_images(urls, output_folder):
    errors = 0
    skipped = 0
    imgs_count = 0
    with tqdm(total = len(urls), desc="downloading images") as pbar:
        for url in urls:
            try:
                response = requests.get(url, headers=user_agent, timeout=skip_delay)
                response.raise_for_status()
                img = Image.open(BytesIO(response.content))
                if(check_img(img.size)):
                    img = processing_img(img, target_size)
                    output_path = os.path.join(output_folder, f'image_{imgs_count}.{target_format.lower()}')
                    img.convert("RGB").save(output_path, target_format)
                    imgs_count+=1
                else:
                    skipped+=1
            except Exception as e:
                # print(e)
                errors+=1
            pbar.update(1)
    if(errors):
        print(f"Errors occured: {errors}")
    if(skipped):
        print(f"Skipped images: {skipped}")

def save_links_to_file(links, output_folder):
    with open(os.path.join(output_folder, 'image_links.txt'), 'w') as f:
        for link in links:
            f.write(f"{link}\n")

prompt = input("Enter your search term: ")
num_links = int(input("Enter the required quantity: "))
output_folder = "images/" + (input("Enter the name of the download folder: "))

os.makedirs(output_folder, exist_ok=True)

image_links = []
start = 1

while(num_links>0):
    if(num_links>=10):
        image_links += get_img_links(prompt, 10, api_key, cse_id, start)
        start+=10
        num_links-=10
    else:
        image_links += get_img_links(prompt, num_links, api_key, cse_id, start)
        num_links = 0

save_links_to_file(image_links, output_folder)
download_images(image_links, output_folder)