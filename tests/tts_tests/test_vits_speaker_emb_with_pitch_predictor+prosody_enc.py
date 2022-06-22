import glob
import os
import shutil

from trainer import get_last_checkpoint

from tests import get_device_id, get_tests_output_path, run_cli
from TTS.tts.configs.vits_config import VitsConfig

config_path = os.path.join(get_tests_output_path(), "test_model_config.json")
output_path = os.path.join(get_tests_output_path(), "train_outputs")


config = VitsConfig(
    batch_size=2,
    eval_batch_size=2,
    num_loader_workers=0,
    num_eval_loader_workers=0,
    text_cleaner="english_cleaners",
    use_phonemes=True,
    phoneme_language="en-us",
    phoneme_cache_path="tests/data/ljspeech/phoneme_cache/",
    run_eval=True,
    test_delay_epochs=-1,
    epochs=1,
    print_step=1,
    print_eval=True,
    compute_pitch=True,
    f0_cache_path="tests/data/ljspeech/f0_cache/",
    test_sentences=[
       ["Be a voice, not an echo.", "ljspeech-1", "tests/data/ljspeech/wavs/LJ001-0001.wav", None, None, "ljspeech-2"],
    ],
)
# set audio config
config.audio.do_trim_silence = True
config.audio.trim_db = 60

# active multispeaker d-vec mode
config.model_args.use_speaker_embedding = True
config.model_args.use_d_vector_file = False
config.model_args.d_vector_file = "tests/data/ljspeech/speakers.json"
config.model_args.speaker_embedding_channels = 128
config.model_args.d_vector_dim = 128


config.model_args.use_precomputed_alignments = True
config.model_args.alignments_cache_path = "tests/data/ljspeech/mas_alignments/alignments/"

# pitch predictor
config.model_args.use_pitch = True
config.model_args.use_pitch_on_enc_input = False
config.model_args.pitch_embedding_dim = 2
config.model_args.condition_dp_on_speaker = False



# prosody encoder
config.model_args.use_prosody_encoder = True
config.model_args.prosody_embedding_dim = 64
config.model_args.prosody_encoder_type = "resnet"

config.model_args.use_encoder_conditional_module = True
config.model_args.use_z_decoder = False

config.model_args.use_latent_discriminator = False

config.save_json(config_path)
# train the model for one epoch
command_train = (
    f"CUDA_VISIBLE_DEVICES='{get_device_id()}' python TTS/bin/train_tts.py --config_path {config_path} "
    f"--coqpit.output_path {output_path} "
    "--coqpit.datasets.0.name ljspeech_test "
    "--coqpit.datasets.0.meta_file_train metadata.csv "
    "--coqpit.datasets.0.meta_file_val metadata.csv "
    "--coqpit.datasets.0.path tests/data/ljspeech "
    "--coqpit.datasets.0.meta_file_attn_mask tests/data/ljspeech/metadata_attn_mask.txt "
    "--coqpit.test_delay_epochs 0"
)
run_cli(command_train)

# Find latest folder
continue_path = max(glob.glob(os.path.join(output_path, "*/")), key=os.path.getmtime)

# Inference using TTS API
continue_config_path = os.path.join(continue_path, "config.json")
continue_restore_path, _ = get_last_checkpoint(continue_path)
out_wav_path = os.path.join(get_tests_output_path(), "output.wav")
speaker_id = "ljspeech-1"
continue_speakers_path = os.path.join(continue_path, "speakers.json")


inference_command = f"CUDA_VISIBLE_DEVICES='{get_device_id()}' tts --text 'This is an example.' --speaker_idx {speaker_id} --speakers_file_path {continue_speakers_path} --config_path {continue_config_path} --model_path {continue_restore_path} --out_path {out_wav_path} "
run_cli(inference_command)

# restore the model and continue training for one more epoch
command_train = f"CUDA_VISIBLE_DEVICES='{get_device_id()}' python TTS/bin/train_tts.py --continue_path {continue_path} "
run_cli(command_train)
shutil.rmtree(continue_path)