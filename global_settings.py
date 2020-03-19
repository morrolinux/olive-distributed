class GlobalSettings:
    def __init__(self):
        self.dispatcher = {'chunk_size': 60}
        self.ffmpeg = {'encoder': ['-c:v', 'libx264', '-crf', '23', '-c:a', 'copy'],
                       'gpu_encoder': ['-c:v', 'h264_vaapi', '-qp', '20', '-c:a', 'copy'],
                       'gpu': False}


settings = GlobalSettings()
