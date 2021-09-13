# from vad import extract_speak_segments
import torchaudio
import torch
import librosa
from transformers import Wav2Vec2Processor, Wav2Vec2ForCTC
import json

from pyannote.audio.pipelines import VoiceActivityDetection
from language_files import get_model

pipeline = VoiceActivityDetection(segmentation="pyannote/segmentation")

HYPER_PARAMETERS = {
  # onset/offset activation thresholds
  "onset": 0.5, "offset": 0.5,
  # remove speech regions shorter than that many seconds.
  "min_duration_on": 0.0,
  # fill non-speech regions shorter than that many seconds.
  "min_duration_off": 0.0
}

def extract_speak_segments(audio_path):
    pipeline.instantiate(HYPER_PARAMETERS)
    vad = pipeline(audio_path)
    # print("extracting speaker segments")
    # print(vad)
    return(vad.for_json())

def change_sample_rate(audio_path, new_sample_rate=16000):
    audio_to_resample, sr = librosa.load(audio_path)
    resampled_audio = librosa.resample(audio_to_resample, sr, new_sample_rate)
    resampled_tensor = torch.tensor([resampled_audio])
    return resampled_tensor

def transcribe_from_audio_path_split_on_speech(audio_path, language="Swedish", model="", save_to_file=""):
    waveform, sample_rate = torchaudio.load(audio_path)
    if sample_rate != 16000:
        ## change sample rate to 16000
        waveform = change_sample_rate(audio_path)
        sample_rate = 16000

    segments = extract_speak_segments(audio_path)
    #print("are the segements working", segments)
    transcriptions = []

    model_id = get_model(language)
    if model:
        model_id = model

    processor = Wav2Vec2Processor.from_pretrained(model_id)
    model = Wav2Vec2ForCTC.from_pretrained(model_id)

    for segment in segments['content']:
        
        x = waveform[:,int(segment['segment']['start']*sample_rate): int(segment['segment']['end']*sample_rate)]
        with torch.no_grad():
            logits = model(x).logits
        pred_ids = torch.argmax(logits, dim=-1)
        transcription = processor.batch_decode(pred_ids)
        # print(transcription)

        full_transcript = {   
            "transcription": transcription[0],
            "start": segment['segment']['start'],
            "end": segment['segment']['end']
        }

        transcriptions.append(full_transcript)
        if (save_to_file):
            f = open(save_to_file, "a")
            f.write(json.dumps(full_transcript))
            f.close()

    return transcriptions

# file_path = "./test.wav"
# output = transcribe_from_audio_path_split_on_speech(file_path, "English")
# print(output)