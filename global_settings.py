class GlobalSettings:
    def __init__(self):
        self.dispatcher = dict()
        self.ffmpeg = {'encoder': ['-c:v', 'libx264', '-crf', '23', '-c:a', 'copy']}


settings = GlobalSettings()
