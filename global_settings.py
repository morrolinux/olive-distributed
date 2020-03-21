class GlobalSettings:
    def __init__(self):
        self.dispatcher = {'chunk_size': 60}
        self._ffmpeg_audio = ['-c:a', 'aac', '-b:a', '256k']
        self.ffmpeg = {'encoder': ['-c:v', 'libx264', '-crf', '23'] + self._ffmpeg_audio,
                       'gpu_encoder': ['-c:v', 'h264_vaapi', '-qp', '28', '-rc_mode', 'ICQ'] + self._ffmpeg_audio,
                       'gpu': False}
        self.nfs_tuning = ['-o', 'rsize=131072,wsize=131072,noatime,nodiratime,nolock,soft,timeo=30']

settings = GlobalSettings()
