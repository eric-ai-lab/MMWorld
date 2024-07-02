# from moviepy.editor import VideoFileClip
# from pytube import YouTube
import sys
import os

import base64

def calculate_video_length(video_path):
    try:
        with VideoFileClip(video_path) as video:
            return video.duration
    except Exception as e:
        print(f"Error calculating video length for {video_path}: {e}")
        return 0
    

def show_progress(stream, chunk, bytes_remaining):
    total_size = stream.filesize
    bytes_downloaded = total_size - bytes_remaining 
    sys.stdout.write(f"Downloading: {bytes_downloaded / total_size * 100:.2f}%\r")
    sys.stdout.flush()


def answer_post_processing(model_answer):
    parts = model_answer.split('.')
    model_answer_processed = parts[0].replace("The answer is", "").strip().lower().strip("\"'")
    model_answer_label = model_answer_processed.split(':')[0].strip()
    return model_answer_label


def format_time(seconds):
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    seconds = int(seconds % 60)
    return f"{hours:02}:{minutes:02}:{seconds:02}"


def get_transcript_with_formatted_time(video_url):
    video_id = extract_video_id(video_url)
    if video_id is None:
        return "Invalid YouTube URL or Video ID not found"
    return YouTubeTranscriptApi.get_transcript(video_id)


def encode_images_to_base64(directory):
    images_base64 = []
    for image_name in os.listdir(directory):
        image_path = os.path.join(directory, image_name)
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode()
            images_base64.append({"image": encoded_string})
    return images_base64


def download_video(url, video_id, output_path):
    if os.path.exists(output_path):
        print(f"Video with {url} already downloaded. Skipping download.")
        return output_path
    try:
        if "shorts" in url:
            video_id = video_id.replace("shorts/", "")
            print(f"Shorts video detected. ")
        yt = YouTube(url, on_progress_callback=show_progress)
        video_stream = yt.streams.filter(progressive=True, file_extension='mp4').order_by('resolution').desc().first()
        if video_stream:
            video_stream.download(output_path=output_path, filename=f"{video_id}.mp4")
            print(f"\nDownloaded {yt.title} successfully.")
            return True
        else:
            print("No suitable video stream found for:", url)
            return False
    except Exception as e:
        print(f"Error downloading video {url}: {e}")
        return False


def compute_question_accuracy(model_answer, correct_answer_label, options):
    return model_answer == correct_answer_label.lower().strip()


def compute_question_accuracy_with_gpt(answer_evaluator, model_answer, correct_answer_label, question, options):
    options_str = "\n".join([f"Option {label.upper()}: {text}" for label, text in options.items()])
    # prompt = (f"I will present a response from a question-answering model and several answer options. "
    #           f"Your task is to evaluate the response and determine which of the following options it most closely aligns with.\n\n"
    #           f"Response: '{model_answer}'\n\n"
    #           f"Options:\n{options_str}\n\n"
    #           "Indicate the most similar option by responding with the corresponding letter only (a, b, c, or d).")
    prompt="For question: "+question+"\n"\
        + options_str \
        + "(please select one)\nGround truth answer: "\
        + correct_answer_label\
        + "\nModel predicted answer: "+model_answer\
        + "\nBased on the question and the ground truth answer, is the model's predicted answer correct? If multi-choice provided, think about which choice is selected by the model, is it correct? (please answer yes/no)\n"
    try:
        response = answer_evaluator.chat.completions.create(
            model="xx",
            messages=[
                {"role": "system", "content": "You are a helpful assistant that provides concise answers."},
                {"role": "user", "content": prompt}
            ]
        )

       
    except Exception as e:
        print(f"Error evaluating response: {e}")
        # ai_response = model_answer
        return 'Error', False
    ai_response = response.choices[0].message.content.strip().lower()
    if "yes" in ai_response :
        gpt_judge_correct = True
    else:
        gpt_judge_correct = False
    return ai_response, gpt_judge_correct



def gpt(question, options, prompt):
            constructed_url = 'xx'
            headers = {
                'Content-Type': 'application/json',
                "api-key": "xx",
            }

            def run_api(body):
                request = requests.post(constructed_url, headers=headers, json=body)
                response = request.json()
                return response

            body = [{   
                        'role' : 'system',
                        'content' : ['You are an expert in assisting human. Follows the user prompt in a completion mode. Generate precise and clear response. End your response with {END}.'],
                    },
                    {   
                        'role' : 'user',
                        'content' : [prompt],  
                    },
            ]

            inputs = {}
            inputs['messages'] = body # for "chat"
            inputs['max_tokens'] = 1024
            inputs['stop'] = "{END}"
            results = run_api(inputs)
            return results
        
def gpt4v(question, options, prompt, video, video_id):
    no_of_frames_to_returned = 8

    videoframefolder = f"./video_benchmark/clipped_video/{video_id}"
    if not os.path.exists(videoframefolder):
        os.makedirs(videoframefolder)
        diskwriter = KeyFrameDiskWriter(location=videoframefolder)
        video_file_path = video

        print(f"Input video file path = {video_file_path}")


        try:
            vd.extract_video_keyframes(
                no_of_frames=no_of_frames_to_returned, file_path=video_file_path,
                writer=diskwriter
            )
        except Exception as e:
            print(f"Error in extracting video keyframes: {e}")
            images_base64 = []

    
    if len(os.listdir(videoframefolder)) == 0:
        images_base64 = []
    else:
        images_base64 = encode_images_to_base64(videoframefolder)
    constructed_url = 'xx'
    headers = {
        'Content-Type': 'application/json',
        'api-key': 'xx'
    }

    def run_api(body):
        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()
        return response

    prompt = f"Based on the following video frames extracted from the video, answer the question {question} by selecting one from the giving answers {options}."

    body = [{   
                'role' : 'system',
                'content' : ['You are an expert in assisting human. Follows the user prompt in a completion mode. Generate precise and clear response. End your response with {END}.'],
            },
            {   
                'role' : 'user',
                'content' : [prompt, *images_base64],  
            },
    ]

    inputs = {}
    inputs['messages'] = body 
    inputs['max_tokens'] = 1024
    inputs['stop'] = "{END}"
    results = run_api(inputs)
    return results

def gpt4o(question, options, prompt, video, video_id):
    no_of_frames_to_returned = 8

    videoframefolder = f"./video_benchmark/clipped_video/{video_id}"
    if not os.path.exists(videoframefolder):
        os.makedirs(videoframefolder)
        diskwriter = KeyFrameDiskWriter(location=videoframefolder)
        video_file_path = video

        print(f"Input video file path = {video_file_path}")


        try:
            vd.extract_video_keyframes(
                no_of_frames=no_of_frames_to_returned, file_path=video_file_path,
                writer=diskwriter
            )
        except Exception as e:
            print(f"Error in extracting video keyframes: {e}")
            images_base64 = []

    
    if len(os.listdir(videoframefolder)) == 0:
        images_base64 = []
    else:
        images_base64 = encode_images_to_base64(videoframefolder)
    api_base = "xx" 
    deployment_name = "xx" 
    api_version = "2024-03-01-preview"
    constructed_url = f"{api_base}/openai/deployments/{deployment_name}/chat/completions?api-version={api_version}"
    headers = {
        'Content-Type': 'application/json',
        'api-key': 'xx'
    }

    def run_api(body):
        request = requests.post(constructed_url, headers=headers, json=body)
        response = request.json()
        return response

    prompt = f"Based on the following video frames extracted from the video, answer the question {question} by selecting one from the giving answers {options}."


    body = [
            {
                'role': 'system',
                'content': 'You are an expert in assisting humans. Follow the user prompt in a completion mode. Generate precise and clear response. End your response with {END}.'
            },
            {
                'role': 'user',
                'content': prompt
            },
            {
                'role': 'user',
                'content': images_base64
            }
        ]

    inputs = {}
    inputs['messages'] = body # for "chat"
    inputs['max_tokens'] = 2000
    inputs['stop'] = "{END}"
    results = run_api(inputs)
    return results