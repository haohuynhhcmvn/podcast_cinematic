# ============================================================
# 🔥 WAVEFORM RIPPLE – FULL TRANSPARENT + KHÔNG BAO GIỜ LỖI
# ============================================================
def make_circular_waveform(audio_path, duration, width=1920, height=1080):
    fps = 30
    pulse_interval = 0.35
    max_radius = min(width, height) // 2
    speed = 420

    audio = AudioSegment.from_file(audio_path)
    samples = np.array(audio.get_array_of_samples()).astype(np.float32)

    if audio.channels == 2:
        samples = samples.reshape((-1, 2)).mean(axis=1)

    max_val = np.max(np.abs(samples))
    if max_val > 0:
        samples /= max_val

    sample_rate = audio.frame_rate

    def get_amp(t):
        idx = int(t * sample_rate)
        if idx < 0 or idx >= len(samples):
            return 0
        return abs(samples[idx])

    cx, cy = width // 2, height // 2

    # ⭐ Frame RGB: nền đen (không quan trọng, vì mask sẽ quyết định opacity)
    def make_rgb_frame(t):
        return np.zeros((height, width, 3), dtype=np.uint8)

    # ⭐ Frame MASK: grayscale float (0–1)
    def make_mask_frame(t):
        mask = np.zeros((height, width), dtype=np.float32)

        pulse_count = int(t / pulse_interval)

        for i in range(pulse_count):
            pulse_t = i * pulse_interval
            age = t - pulse_t
            if age < 0:
                continue

            r = int(speed * age)
            if r > max_radius:
                continue

            amp = get_amp(pulse_t)
            alpha = (1 - age / (max_radius / speed)) * amp
            alpha = max(0, min(alpha, 1))

            if alpha < 0.002:
                continue

            thickness = 4

            yy, xx = np.ogrid[:height, :width]
            dist = np.sqrt((xx - cx)**2 + (yy - cy)**2)
            ring = np.logical_and(dist >= r - thickness, dist <= r + thickness)

            mask[ring] = alpha

        return mask

    # Tạo clip + mask
    clip = VideoClip(make_rgb_frame, duration=duration).set_fps(fps)
    mask = VideoClip(make_mask_frame, duration=duration).set_fps(fps)

    # ⭐ BẮT BUỘC — nếu không sẽ bị AssertionError
    mask.ismask = True

    # Gắn mask
    clip = clip.set_mask(mask)

    return clip
