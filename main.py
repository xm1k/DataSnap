from sympy.physics.units import current

api_key_list = ['To work you need API_KEY from !Custom Search API! You can use more than one key']
from config import api_key_list # Comment this if you don't need to store the keys in another file
current_api_key = 0
api_key = api_key_list[current_api_key]
import os
import requests
import time
import random

from PIL import Image
from io import BytesIO
from tqdm import tqdm

cse_id = '431e5b8b2faec4801'

max_size = (-1,-1) # -1 if without restrictions on permission
target_size = (256,256)
target_format = 'JPEG'
crop_threshold = 0.5 # Acceptable image crop percentage
imgs_count = 0
skip_delay = 10 # Load wait time

exceptions = [ # These headers will be strictly excluded from requests
    "youtube",
    "video",
    "thumbnail",
    "cdn",
    "instagram"
]

prompts = [ # These headers will be included in the request, too much is not recommended
    "cat",
    "high-resolution"
]

user_agent = {
    'User-Agent':'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36'
}

def create_prompts(base_prompt):
    exclusions = " ".join([f"-{word}" for word in exceptions])
    additions = " ".join(prompts)
    return f"{base_prompt} {additions} {exclusions}".strip()


def get_img_links(prompt, links_count, start):
    global current_api_key
    prompt = create_prompts(prompt)
    url = "https://www.googleapis.com/customsearch/v1"

    params = {
        'q': prompt,
        'cx': cse_id,
        'searchType': 'image',
        'key': api_key_list[current_api_key],
        'num': links_count,
        'start': start
    }
    while True:
        try:
            response = requests.get(url, params=params, headers=user_agent, timeout=skip_delay)
            response.raise_for_status()
            data = response.json()
            if 'items' in data:
                return [item['link'] for item in data['items']]
            else:
                return []
        except requests.exceptions.HTTPError as e:
            print(f"Error with API key {current_api_key}: {e}")
            if e.response.status_code == 400:
                if start > 200: # For some reason, when start > 200 it gives an error
                    start = random.randint(1, 190)
            elif e.response.status_code == 429:
                current_api_key += 1
                if current_api_key < len(api_key_list):
                    print(f"Switching to API key {current_api_key}")
                    params['key'] = api_key_list[current_api_key]
                else:
                    print("All API keys have been exhausted")
                    return []
            else:
                current_api_key += 1
                if current_api_key < len(api_key_list):
                    print(f"Switching to API key {current_api_key}")
                    params['key'] = api_key_list[current_api_key]
                else:
                    print("All API keys have been exhausted")
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
    imgs_count = len(os.listdir(output_folder)) - 1
    n = 0
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
                    n+=1
                else:
                    skipped+=1
            except Exception as e:
                # print(e)
                errors+=1
            pbar.update(1)
    return n
    if(errors):
        print(f"Errors occured: {errors}")
    if(skipped):
        print(f"Skipped images: {skipped}")

def save_links_to_file(links, output_folder):
    with open(os.path.join(output_folder, 'image_links.txt'), 'w') as f:
        for link in links:
            f.write(f"{link}\n")

def load_existing_links(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return [line.strip() for line in f.readlines()]
    return []

def load_config(file_path):
    with open(file_path, 'r') as f:
        lines = f.readlines()
    num_links = int(lines[0].strip())
    config = [line.strip().split(';') for line in lines[1:]]
    return num_links, config

num_links, config = load_config('config.txt')

for request,output_folder in config:
    output_folder = os.path.join("images", output_folder)
    os.makedirs(output_folder, exist_ok=True)

    existing_links_file = os.path.join(output_folder, 'image_links.txt')
    existing_links = load_existing_links(existing_links_file)
    images_in_folder = len(os.listdir(output_folder)) - 1

    image_links = []

    remaining_links = num_links - images_in_folder
    start = len(existing_links) + 1
    while remaining_links > 0:
        image_links += get_img_links(request, 10, start)
        start += 10
        save_links_to_file(existing_links + image_links, output_folder)
        remaining_links -= download_images(image_links, output_folder)
        existing_links = existing_links + image_links
        image_links = []
        print(len(os.listdir(output_folder)) - 1)
    print(f"{request} --- start = {start}")

print("--- DONE ---")