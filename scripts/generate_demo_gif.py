import os
from PIL import Image, ImageDraw, ImageFont

def create_demo_gif(output_path="assets/demo.gif"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    # 2x High-DPI Dimensions
    W, H = 840, 480
    bg_color = (14, 16, 23)        # #0e1017
    titlebar_color = (22, 24, 33)  # #161821
    border_color = (39, 39, 42)    # #27272a
    
    # Text colors
    c_zinc = (228, 228, 231)       # primary text
    c_muted = (161, 161, 170)      # secondary text
    c_dim = (113, 113, 122)        # tertiary text
    c_accent = (165, 180, 252)     # soft indigo/lavender
    c_mint = (110, 231, 183)       # soft mint green
    c_ochre = (253, 224, 71)       # soft amber
    c_cyan = (125, 211, 252)       # soft cyan
    c_box_bg = (18, 20, 28)        # card background
    c_card_border = (42, 45, 61)   # card border
    c_fail_bg = (23, 20, 27)       # failover card bg
    c_fail_border = (65, 45, 30)   # failover card border

    # Fonts
    font_path = r"C:\Windows\Fonts\consola.ttf"
    font = ImageFont.truetype(font_path, 14)
    font_bold = ImageFont.truetype(r"C:\Windows\Fonts\consolab.ttf" if os.path.exists(r"C:\Windows\Fonts\consolab.ttf") else font_path, 14)
    font_sm = ImageFont.truetype(font_path, 12)
    font_title = ImageFont.truetype(font_path, 12)

    def draw_base_window():
        im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        draw = ImageDraw.Draw(im)
        
        # Rounded window container
        draw.rounded_rectangle([10, 10, W - 10, H - 10], radius=10, fill=bg_color, outline=border_color, width=1)
        
        # Titlebar
        draw.rounded_rectangle([10, 10, W - 10, 46], radius=10, fill=titlebar_color)
        draw.rectangle([10, 36, W - 10, 46], fill=titlebar_color) # square off bottom corners of titlebar
        draw.line([10, 46, W - 10, 46], fill=border_color, width=1)
        
        # Traffic lights
        draw.ellipse([26, 23, 36, 33], fill=(239, 68, 68))
        draw.ellipse([42, 23, 52, 33], fill=(245, 158, 11))
        draw.ellipse([58, 23, 68, 33], fill=(16, 185, 129))
        
        # Title
        draw.text((W // 2 - 120, 22), "claude-pool — automatic session failover", font=font_title, fill=c_dim)
        return im

    frames = []
    durations = []

    # Frame generator helper
    def add_frame(draw_content_fn, count=1, duration=150):
        for _ in range(count):
            base = draw_base_window()
            d = ImageDraw.Draw(base)
            draw_content_fn(d)
            # Convert to RGB with palette for clean GIF compression
            rgb = Image.new("RGB", base.size, (10, 10, 12))
            rgb.paste(base, mask=base.split()[3])
            frames.append(rgb.quantize(colors=128, method=Image.Quantize.MEDIANCUT))
            durations.append(duration)

    # 1. Terminal Prompt states
    prompt_cmd = "claude-pool"
    for i in range(len(prompt_cmd) + 1):
        typed = prompt_cmd[:i]
        def draw_typing(d, t=typed, show_cursor=(i % 2 == 0)):
            d.text((36, 64), "developer@workstation", font=font_bold, fill=c_mint)
            d.text((215, 64), ":", font=font, fill=c_dim)
            d.text((226, 64), "~/projects/api", font=font, fill=c_cyan)
            d.text((345, 64), "$", font=font, fill=c_dim)
            d.text((362, 64), t, font=font_bold, fill=c_zinc)
            if show_cursor:
                cx = 362 + int(font.getlength(t))
                d.rectangle([cx + 2, 66, cx + 10, 78], fill=c_accent)
        add_frame(draw_typing, count=1, duration=70 if i < len(prompt_cmd) else 350)

    # 2. HUD Card appears
    def draw_hud(d):
        # Prompt line
        d.text((36, 64), "developer@workstation", font=font_bold, fill=c_mint)
        d.text((215, 64), ":", font=font, fill=c_dim)
        d.text((226, 64), "~/projects/api", font=font, fill=c_cyan)
        d.text((345, 64), "$", font=font, fill=c_dim)
        d.text((362, 64), "claude-pool", font=font_bold, fill=c_zinc)
        
        # HUD Card
        d.rounded_rectangle([36, 92, W - 36, 186], radius=8, fill=c_box_bg, outline=c_card_border, width=1)
        d.rounded_rectangle([36, 92, 145, 114], radius=6, fill=(27, 30, 43))
        d.text((48, 96), "claude-pool", font=font_sm, fill=c_accent)
        
        # Row 1: Active
        d.ellipse([54, 128, 62, 136], fill=c_mint)
        d.text((72, 124), "active", font=font_bold, fill=c_zinc)
        d.text((130, 124), "primary", font=font, fill=c_zinc)
        d.text((195, 124), "(P1)", font=font, fill=c_dim)
        d.text((230, 124), "·", font=font, fill=c_dim)
        d.text((245, 124), "97% session left", font=font_bold, fill=c_mint)
        d.text((385, 124), "(resets in 4h 12m)", font=font, fill=c_dim)

        # Row 2: Standby
        d.ellipse([54, 148, 62, 156], outline=c_dim, width=1)
        d.text((72, 144), "standby", font=font, fill=c_dim)
        d.text((140, 144), "account4 (P2), backup (P3)", font=font, fill=c_muted)

        # Row 3: Pool
        d.text((54, 163), "◌", font=font_sm, fill=c_accent)
        d.text((72, 163), "pool", font=font, fill=c_dim)
        d.text((140, 163), "193.4M tokens today across 3 accounts", font=font, fill=c_muted)

    add_frame(draw_hud, count=1, duration=1400)

    # 3. Claude interaction starts
    def draw_claude_start(d):
        draw_hud(d)
        d.text((36, 212), ">", font=font_bold, fill=c_accent)
        d.text((54, 212), "Refactor auth middleware to use redis token cache", font=font, fill=c_zinc)

    add_frame(draw_claude_start, count=1, duration=900)

    # 4. Claude thinking
    def draw_claude_working(d):
        draw_claude_start(d)
        d.text((36, 238), "● Thinking... reading src/auth.ts and config.ts", font=font, fill=c_dim)
        d.text((36, 260), "✓ Generated updated middleware (4 files modified)", font=font, fill=c_mint)

    add_frame(draw_claude_working, count=1, duration=1100)

    # 5. Limit hit alert
    def draw_limit_hit(d):
        draw_claude_working(d)
        d.rounded_rectangle([36, 290, W - 36, 324], radius=6, fill=(33, 25, 18), outline=(72, 48, 26), width=1)
        d.text((52, 298), "⚠️  Anthropic 5-hour rolling limit reached on account 'primary'", font=font_bold, fill=c_ochre)

    add_frame(draw_limit_hit, count=1, duration=1200)

    # 6. Scene 2: Auto-Failover transition takes center stage
    def draw_failover(d):
        d.rounded_rectangle([36, 64, W - 36, 188], radius=8, fill=c_fail_bg, outline=c_fail_border, width=1)
        d.rounded_rectangle([36, 64, 190, 88], radius=6, fill=(45, 32, 26))
        d.text((48, 69), "failover transition", font=font_sm, fill=c_ochre)

        d.text((54, 102), "Rate limit reached on primary", font=font_bold, fill=c_ochre)

        d.ellipse([54, 128, 62, 136], fill=c_mint)
        d.text((72, 124), "preserved session", font=font, fill=c_dim)
        d.text((220, 124), "4e00c501-e0c9-4b2a-874a...", font=font, fill=c_zinc)

        d.ellipse([54, 148, 62, 156], fill=c_mint)
        d.text((72, 144), "synchronized state", font=font, fill=c_dim)
        d.text((220, 144), ".jsonl transcripts mirrored to account4", font=font, fill=c_zinc)

        d.text((54, 164), "→", font=font_bold, fill=c_accent)
        d.text((72, 164), "continuing on", font=font_bold, fill=c_mint)
        d.text((220, 164), "account4", font=font_bold, fill=c_zinc)
        d.text((290, 164), "(promoted to Priority 1)", font=font, fill=c_dim)

    add_frame(draw_failover, count=1, duration=1100)

    # 7. Resumed on Account 4 seamlessly
    def draw_resumed(d, show_cursor=True):
        draw_failover(d)
        d.text((36, 214), "Resuming conversation 4e00c501-e0c9-4b2a on account4...", font=font, fill=c_dim)
        
        d.rounded_rectangle([36, 242, W - 36, 280], radius=6, fill=(16, 25, 21), outline=(29, 59, 43), width=1)
        d.text((52, 252), "✓ Seamless failover complete: 100% conversation memory intact.", font=font_bold, fill=c_mint)

        d.text((36, 302), "All 14 unit tests passing. What would you like to build next?", font=font, fill=c_zinc)

        d.text((36, 334), ">", font=font_bold, fill=c_accent)
        if show_cursor:
            d.rectangle([54, 336, 62, 348], fill=c_accent)

    add_frame(lambda d: draw_resumed(d, True), count=1, duration=1500)
    add_frame(lambda d: draw_resumed(d, False), count=1, duration=600)
    add_frame(lambda d: draw_resumed(d, True), count=1, duration=1800)

    # Save animated GIF
    frames[0].save(
        output_path,
        save_all=True,
        append_images=frames[1:],
        duration=durations,
        loop=0,
        optimize=True
    )
    print(f"Generated {output_path}: {len(frames)} frames, {os.path.getsize(output_path) / 1024:.1f} KB")

if __name__ == "__main__":
    create_demo_gif()
