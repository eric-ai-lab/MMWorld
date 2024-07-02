import json
import sys
import os
import PIL.Image
import glob

import requests
import time
import argparse

import argparse
from main_utils import *
from openai import AzureOpenAI

import copy

from Katna.video import Video
from Katna.writer import KeyFrameDiskWriter
vd = Video()






def answer_generator(answer_evaluator, video_file, question, options, correct_answer, correct_answer_label, question_type, annotations, video_id, detailed_results, subject_data, modelname, tokenizer=None, processor=None, image_processor=None):
    prompt = f"Answer the question {question} by selecting one from the giving answers {options}. Respond with only single letter such as a, b, c ,d."
    # prompt = f"Answer the question {question} by selecting one from the giving answers {options}. Also give reasons of why you select this answer after your selelcted amswer."
    subject_data["total_questions"] += 1

    
    
    if modelname == 'gpt' or modelname == 'gpt4o': 
        max_retries= 3000000
        retry_delay = 0.0001 
        retry_count = 0

        while retry_count < max_retries:
            if modelname == 'gpt':
                model_response = gpt4v(question, options, prompt, video_file, video_id)
            elif modelname == 'gpt4o':
                model_response = gpt4o(question, options, prompt, video_file, video_id)
            if 'choices' in model_response:
                model_answer = model_response['choices'][0]['message']['content']
                print('The model answer is:', model_answer)
                break
            elif model_response['error']['code'] == '429':
                print(f"Rate limit exceeded. Error message is {model_response}, Retrying in {retry_delay} seconds..., retry count: {retry_count}")
                time.sleep(retry_delay)
            elif model_response['error']['code'] == 'content_filter':
                print(f"Content filter triggered. Error message is {model_response}, Retrying in {retry_delay} seconds..., retry count: {retry_count}")
                model_answer = 'content_filter'
                time.sleep(retry_delay)
                break
            elif 'error' in model_response:
                print(f"Error message is {model_response['error']['message']}, Retrying in {retry_delay} seconds..., retry count: {retry_count}")
                model_answer = model_response['error']['message']
                time.sleep(retry_delay)
                break

            retry_count += 1
        print('Model selected: gpt, question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'gemini':
        safety_settings = [
        {
            "category": "HARM_CATEGORY_DANGEROUS",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HARASSMENT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_HATE_SPEECH",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
            "threshold": "BLOCK_NONE",
        },
        {
            "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
            "threshold": "BLOCK_NONE",
        },
    ]
        no_of_frames_to_returned = 10

        videoframefolder = f"./clipped_video/{video_id}"
        images = [] 
        if os.path.exists(videoframefolder) and len(os.listdir(videoframefolder)) > 0:
            for image_file_name in os.listdir(videoframefolder):
                image_path = os.path.join(videoframefolder, image_file_name)
                try:
                    img = PIL.Image.open(image_path)
                    images.append(img)
                except Exception as e:
                    print(f"Error loading image {image_file_name}: {e}")
        else:
            if not os.path.exists(videoframefolder):
                os.makedirs(videoframefolder)
            diskwriter = KeyFrameDiskWriter(location=videoframefolder)
            video_file_path = videofile

            print(f"Input video file path = {video_file_path}")


            try:
                vd.extract_video_keyframes(
                    no_of_frames=no_of_frames_to_returned, file_path=video_file_path,
                    writer=diskwriter
                )
                image_path = os.path.join(videoframefolder, image_file_name)
                img = PIL.Image.open(image_path)
                images.append(img)
            except Exception as e:
                print(f"Error in extracting video keyframes: {e}")

        if images:
            for attempt in range(5):  
                try:
                    model_answer = models.generate_content([prompt] + images, safety_settings=safety_settings).text
                    break
                except Exception as e:
                    print(f"Attempt {attempt+1} failed: {e}")
                    if attempt == 4:
                        model_answer = 'error'
        else:
            print("No images found in the directory.")
            model_answer = 'No images to process.'
        print('Model selected: gemini, question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'claude': 
        import anthropic
        from io import BytesIO

        client = anthropic.Anthropic(
            api_key="xx",
        )

        no_of_frames_to_returned = 10

        videoframefolder = f"./video_benchmark/clipped_video/{video_id}"
        images = [] 
        if os.path.exists(videoframefolder) and len(os.listdir(videoframefolder)) > 0:
            for image_file_name in os.listdir(videoframefolder):
                image_path = os.path.join(videoframefolder, image_file_name)
                try:
                    img = PIL.Image.open(image_path)
                    buffered = BytesIO()
                    img.save(buffered, format="JPEG")
                    img_base64 = base64.b64encode(buffered.getvalue()).decode("utf-8")
                    images.append(img_base64)
                except Exception as e:
                    print(f"Error loading image {image_file_name}: {e}")


        message_content = []

        for img_base64 in images:
            message_content.append(
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": img_base64,
                    },
                }
            )


        message_content.append(
            {
                "type": "text",
                "text": prompt
            }
        )


        messages_payload = [{"role": "user", "content": message_content}]
        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=1024,
            messages=messages_payload,
        )

        model_answer = message.content[0].text
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'videochat': 
        model_answer = videochat_answer(models, video_file, question, options)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'videollama': 
        model_answer = videollama_answer(models, video_file, question, options)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'chatunivi':
        model_answer = chatunivi_answer(models, video_file, question, options, prompt, tokenizer)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'mplugowl':
        model_answer = mplugowl_answer(models, video_id, video_file, question, options, prompt, tokenizer, image_processor)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'otter':
        model_answer = otter_answer(models, video_file, question, options, prompt, image_processor)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif 'xinstruct' in modelname:
        model_answer = xinstruct_answer(models, video_file, question, options, image_processor)
        model_answer = answer_post_processing(model_answer)
        print('Model selected: xinstruct, question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'pandagpt':
        model_answer = pandagpt_answer(models, video_file, question, options, prompt)
        model_answer = answer_post_processing(model_answer)
        print('Model selected: PandaGPT, question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'imagebind_llm':
        model_answer = imagebind_llm_answer(models, video_file, question, options, prompt)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'lwm':
        model_answer = lwm_answer(models, video_file, question, options, prompt)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    elif modelname == 'videollava':
        model_answer = videollava_answer(models, video_file, question, options, prompt, tokenizer, processor, video_processor)
        model_answer = answer_post_processing(model_answer)
        print('Model selected:', modelname, 'question:', question, 'options:', options, 'answer:', model_answer)
    else:
        print("Invalid model name. Exiting.")
        sys.exit(1)

    gpt_processed_answer, is_correct = compute_question_accuracy_with_gpt(answer_evaluator, model_answer, correct_answer_label, question ,options)
    if is_correct:
        subject_data["correct_answers"] += 1
    
    for annotation, value in annotations.items():
        subject_data["accuracy_per_annotation"].setdefault(annotation, {"total": 0, "correct": 0})
        if value:
            subject_data["accuracy_per_annotation"][annotation]["total"] += 1
        if value and is_correct:
            subject_data["accuracy_per_annotation"][annotation]["correct"] += 1
    
    test = copy.deepcopy(subject_data["accuracy_per_annotation"])
    subject_data["accuracy_per_question_type"].setdefault(question_type, {"total": 0, "correct": 0})
    subject_data["accuracy_per_question_type"][question_type]["total"] += 1
    if is_correct:
        subject_data["accuracy_per_question_type"][question_type]["correct"] += 1

    detailed_results.append({
        "subject": subject,
        "video_id": video_id,
        "question": question,
        "correct_answer": correct_answer,
        "correct_answer_label": correct_answer_label,
        "model_answer": model_answer,
        'gpt_processed_answer': gpt_processed_answer,
        "options": options,
        "is_correct": is_correct,
        "annotations": annotations,
        "question_type": question_type,
        "subject_data": test
    })

    with open(detailed_results_paths[run_idx], 'w') as f:
        json.dump(detailed_results, f, indent=4)
        print(f"Saved detailed results to {detailed_results_paths[run_idx]}")




if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Initialize and run model")
    parser.add_argument("modelname", type=str, help="Name of the model to initialize and run")
    parser.add_argument("--textonly", action="store_true", help="Flag to indicate if the model should run in text-only mode")

    args = parser.parse_args()


    modelname = args.modelname
    textonly = args.textonly



    if modelname == "imagebind_llm":
        sys.path.append(os.path.abspath("./LLaMA-Adapter/imagebind_LLM"))
        from eval_imagebind_llm import imagebind_llm_init, imagebind_llm_answer
    elif modelname == "lwm":
        sys.path.append('./video_benchmark/LWM')
        from eval_LWM import lwm_init, lwm_answer
    elif modelname == "mplugowl":
        sys.path.append('./video_benchmark/mPLUG-Owl2')
        from eval_mplug_owl import mplugowl_init, mplugowl_answer
    elif modelname == "otter":
        sys.path.append('./video_benchmark/otter')
        sys.path.append('./video_benchmark/otter/src')
        from eval_otter import otter_init, otter_answer
    elif modelname == "videochat":
        sys.path.append('./video_benchmark/video_chat2')
        from eval_video_chat import videochat2_init, videochat_answer
    elif modelname == "videollama":
        sys.path.append('./video_benchmark/Video_llama')
        from eval_video_llama import videollama_init, videollama_answer
    elif modelname == "videollava":
        sys.path.append('./video_benchmark/Video-LLaVA')
        from eval_video_llava import videollava_init, videollava_answer
    elif modelname == "xinstruct":
        sys.path.append('./video_benchmark/LAVIS-XInstructBLIP')
        from eval_xinstruct import xinstruct_init, xinstruct_answer
    elif modelname == "pandagpt":
        sys.path.append(os.path.abspath("./PandaGPT"))
        sys.path.append(os.path.abspath('./PandaGPT/code'))
        from eval_pandagpt import pandagpt_init, pandagpt_answer
    elif modelname == "llamaadapter":
        sys.path.append(os.path.abspath("./LLaMA-Adapter/imagebind_LLM"))
        from eval_imagebind_llm import imagebind_llm_init, imagebind_llm_answer


    if modelname == 'gemini':
        import google.generativeai as genai
        models = genai.GenerativeModel('gemini-pro-vision')
        GOOGLE_API_KEY="xx"
        genai.configure(api_key=GOOGLE_API_KEY)

    elif modelname == 'videochat':
        models = videochat2_init()

    elif modelname == 'videollama':
        models = videollama_init()

    elif modelname == 'chatunivi':
        models, tokenizer = chatunivi_init()

    elif modelname == 'otter':
        models, image_processor = otter_init()

    elif modelname == 'mplugowl':
        models, tokenizer, image_processor = mplugowl_init()

    elif modelname == 'xinstruct-7b':
        models, image_processor = xinstruct_init("vicuna7b_v2")

    elif modelname == 'xinstruct-13b':
        models, image_processor = xinstruct_init("vicuna13b")

    elif modelname == 'pandagpt':
        models = pandagpt_init()

    elif modelname == 'imagebind_llm':
        models = imagebind_llm_init()

    elif modelname == 'lwm':
        models = lwm_init()

    elif modelname == 'videollava':
        models, tokenizer, processor, video_processor = videollava_init()







    num_runs = 3

    detailed_results_dir = 'detailed_results'
    final_results_dir = 'final_results'

    detailed_results_paths = [os.path.join(detailed_results_dir, f'{modelname}_detailed_results_{i}.json') for i in range(num_runs)]
    final_results_paths = [os.path.join(final_results_dir, f'{modelname}_final_results_run_{i}.json') for i in range(num_runs)]

    if not os.path.exists(detailed_results_dir):
        os.makedirs(detailed_results_dir )
    if not os.path.exists(final_results_dir):
        os.makedirs(final_results_dir)

    print(f"Using model: {modelname}, textonly: {textonly}")


    videofile = "./video_benchmark/dataset/mmworld.json"
    with open(videofile, 'r') as file:
        dataset = json.load(file)

        

    answer_evaluator = AzureOpenAI(
        azure_endpoint="xx", 
        api_key="xx",
        api_version="2023-12-01-preview"
    )


    for run_idx in range(num_runs):
        total_questions = 0
        correct_answers = 0
        detailed_results = []
        accuracy_per_annotation = {}
        accuracy_per_question_type = {}
        results_by_subject = {}


        failed_downloads = []
        missed_video = set()
        wrong_video = set()
        success_downloads = []


        for video_data in dataset:
            subject = video_data["discipline"]
            if subject not in results_by_subject:
                results_by_subject[subject] = {
                    "total_questions": 0,
                    "correct_answers": 0,
                    "accuracy_per_annotation": {},
                    "accuracy_per_question_type": {},
                    "detailed_results": []
                }
                
            video_id = video_data["video_id"]


            for question_data in video_data["questions"]:
                question = question_data["question"]
                options = question_data["options"]
                
                correct_answer = question_data["answer"]
                correct_answer_label = question_data["correct_answer_label"]
                question_type = question_data["type"]
                requires_video = question_data["requires_visual"]
                annotations = {
                    "requires_audio": question_data["requires_audio"],
                    "requires_domain_knowledge": question_data["requires_domain_knowledge"],
                    "requires_video": requires_video,
                    "question_only": question_data["question_only"]
                }

                video_files = glob.glob(f"./all_data/{video_data['video_id']}/*.mp4")

                if len(video_files) == 0:
                    missed_video.add(video_data["video_id"])
                
                for video_file in video_files:
                    try:
                        answer_generator(answer_evaluator, video_file, question, options, correct_answer, correct_answer_label, question_type, annotations, video_data["video_id"], 
                            results_by_subject[subject]["detailed_results"], results_by_subject[subject], modelname, locals().get('tokenizer', None), locals().get('processor', None), locals().get('image_processor', None))
                    except Exception as e:
                        print(f"Error encountered: {e}")
                        wrong_video.add(video_data["video_id"])
                        

        with open('failed_downloads.json', 'w') as f:
            json.dump(list(missed_video), f, indent=4)
        with open('problemed_video.json', 'w') as f:
            json.dump(list(wrong_video), f, indent=4)

        for subject, data in results_by_subject.items():

            total_questions += data["total_questions"]
            correct_answers += data["correct_answers"]
            for annotation, value in data["accuracy_per_annotation"].items():
                accuracy_per_annotation.setdefault(annotation, {"total": 0, "correct": 0})
                accuracy_per_annotation[annotation]["total"] += value["total"]
                accuracy_per_annotation[annotation]["correct"] += value["correct"]
            for question_type, value in data["accuracy_per_question_type"].items():
                accuracy_per_question_type.setdefault(question_type, {"total": 0, "correct": 0})
                accuracy_per_question_type[question_type]["total"] += value["total"]
                accuracy_per_question_type[question_type]["correct"] += value["correct"]


        overall_accuracy = correct_answers / total_questions * 100
        results = {
            "overall_accuracy": overall_accuracy,
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy_per_annotation": accuracy_per_annotation,
            "accuracy_per_question_type": accuracy_per_question_type,
            "results_by_subject": results_by_subject
        }

        with open(final_results_paths[run_idx], 'w') as file:
            json.dump(results, file, indent=4)
        print(f'Final results saved in {final_results_paths[run_idx]}')

