import os
import math
from PIL import Image, ImageDraw, ImageFont

def create_pool_flow_gif(output_path="assets/pool-flow.gif"):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    W, H = 840, 420
    
    # Palette (Linear/Raycast inspired)
    bg_color = (13, 15, 22)        # #0d0f16
    card_bg = (19, 22, 32)         # #131620
    card_border = (42, 45, 60)     # #2a2d3c
    card_active_bg = (20, 28, 36)  # subtle teal tint
    card_active_border = (45, 95, 80)
    card_warn_bg = (34, 25, 20)    # subtle warm amber tint
    card_warn_border = (90, 55, 30)
    
    c_zinc = (228, 228, 231)       # #e4e4e7
    c_muted = (161, 161, 170)      # #a1a1aa
    c_dim = (113, 113, 122)        # #71717a
    c_accent = (165, 180, 252)     # #a5b4fc (soft lavender/indigo)
    c_mint = (110, 231, 183)       # #6ee7b7 (soft mint)
    c_ochre = (253, 224, 71)       # #fde047 (warm amber)
    c_rose = (253, 164, 175)       # #fda4af
    c_line_dim = (38, 41, 54)      # connection line inactive
    
    # Fonts
    font_mono_path = r"C:\Windows\Fonts\consola.ttf"
    font_sans_path = r"C:\Windows\Fonts\segoeui.ttf"
    
    f_title = ImageFont.truetype(font_sans_path, 16)
    f_title_bold = ImageFont.truetype(font_sans_path, 16)
    f_body = ImageFont.truetype(font_sans_path, 13)
    f_body_bold = ImageFont.truetype(font_sans_path, 13)
    f_mono = ImageFont.truetype(font_mono_path, 12)
    f_mono_bold = ImageFont.truetype(font_mono_path, 12)
    f_badge = ImageFont.truetype(font_sans_path, 11)

    # Coordinates
    # 3 Accounts on the left
    acc_x = 45
    acc_w = 220
    acc_h = 76
    acc_y = [70, 168, 266]
    
    # Hub in the center
    hub_x = 350
    hub_y = 120
    hub_w = 160
    hub_h = 170
    
    # Output on the right
    out_x = 590
    out_y = 135
    out_w = 205
    out_h = 140

    total_frames = 48
    frames = []

    for f in range(total_frames):
        im = Image.new("RGBA", (W, H), bg_color)
        d = ImageDraw.Draw(im)

        # Subtle background dot grid
        for gx in range(20, W, 28):
            for gy in range(20, H, 28):
                d.point((gx, gy), fill=(26, 29, 39))

        # Phases:
        # Phase 1: 0 - 15 (Account 1 active, normal flow)
        # Phase 2: 16 - 24 (Account 1 rate limited, alert triggers)
        # Phase 3: 25 - 34 (Failover transfer to Account 2)
        # Phase 4: 35 - 47 (Account 2 active, uninterrupted output)
        
        phase = 1 if f < 16 else (2 if f < 25 else (3 if f < 35 else 4))
        progress = f / total_frames

        # Top Header
        d.text((45, 24), "CLAUDE POOL ARCHITECTURE", font=f_mono_bold, fill=c_accent)
        d.text((250, 24), "·   Multi-Account Failover & Session Continuity", font=f_mono, fill=c_dim)

        # ----------------- Draw Accounts -----------------
        # Account 1
        if phase == 1:
            # Active
            d.rounded_rectangle([acc_x, acc_y[0], acc_x + acc_w, acc_y[0] + acc_h], radius=8, fill=card_active_bg, outline=card_active_border, width=1)
            d.ellipse([acc_x + 16, acc_y[0] + 18, acc_x + 24, acc_y[0] + 26], fill=c_mint)
            d.text((acc_x + 32, acc_y[0] + 15), "Account 1 (Primary)", font=f_body_bold, fill=c_zinc)
            d.text((acc_x + 32, acc_y[0] + 35), "kbastwad@iprdgroup.com", font=f_mono, fill=c_muted)
            
            # Quota gauge decreasing
            pct = max(5, int(85 - (f / 15.0) * 75))
            gauge_w = 150
            filled_w = int((pct / 100) * gauge_w)
            d.rounded_rectangle([acc_x + 32, acc_y[0] + 55, acc_x + 32 + gauge_w, acc_y[0] + 61], radius=3, fill=(35, 40, 55))
            d.rounded_rectangle([acc_x + 32, acc_y[0] + 55, acc_x + 32 + filled_w, acc_y[0] + 61], radius=3, fill=c_mint if pct > 25 else c_ochre)
            d.text((acc_x + 190, acc_y[0] + 50), f"{pct}%", font=f_mono, fill=c_mint if pct > 25 else c_ochre)
        else:
            # Rate limited / Cooldown
            d.rounded_rectangle([acc_x, acc_y[0], acc_x + acc_w, acc_y[0] + acc_h], radius=8, fill=card_warn_bg, outline=card_warn_border, width=1)
            d.ellipse([acc_x + 16, acc_y[0] + 18, acc_x + 24, acc_y[0] + 26], fill=c_ochre)
            d.text((acc_x + 32, acc_y[0] + 15), "Account 1 (Primary)", font=f_body_bold, fill=c_zinc)
            d.text((acc_x + 32, acc_y[0] + 35), "5-Hour Rolling Limit Hit", font=f_mono, fill=c_ochre)
            d.rounded_rectangle([acc_x + 32, acc_y[0] + 55, acc_x + 32 + 150, acc_y[0] + 61], radius=3, fill=(50, 35, 25))
            d.rounded_rectangle([acc_x + 32, acc_y[0] + 55, acc_x + 32 + 10, acc_y[0] + 61], radius=3, fill=c_rose)
            d.text((acc_x + 190, acc_y[0] + 50), "0%", font=f_mono, fill=c_rose)

        # Account 2
        if phase < 4:
            # Standby (or receiving transfer in phase 3)
            border = c_accent if phase == 3 else card_border
            bg = (25, 28, 42) if phase == 3 else card_bg
            d.rounded_rectangle([acc_x, acc_y[1], acc_x + acc_w, acc_y[1] + acc_h], radius=8, fill=bg, outline=border, width=1)
            d.ellipse([acc_x + 16, acc_y[1] + 18, acc_x + 24, acc_y[1] + 26], outline=c_dim if phase != 3 else c_accent, width=1)
            label = "Account 2 (Standby P2)" if phase != 3 else "Account 2 (Promoting...)"
            d.text((acc_x + 32, acc_y[1] + 15), label, font=f_body_bold, fill=c_zinc if phase == 3 else c_muted)
            d.text((acc_x + 32, acc_y[1] + 35), "mshanbhag@iprdgroup.com", font=f_mono, fill=c_dim)
            d.rounded_rectangle([acc_x + 32, acc_y[1] + 55, acc_x + 32 + 150, acc_y[1] + 61], radius=3, fill=(35, 40, 55))
            d.rounded_rectangle([acc_x + 32, acc_y[1] + 55, acc_x + 32 + 150, acc_y[1] + 61], radius=3, fill=c_accent if phase == 3 else c_dim)
            d.text((acc_x + 190, acc_y[1] + 50), "100%", font=f_mono, fill=c_dim)
        else:
            # Active in Phase 4!
            d.rounded_rectangle([acc_x, acc_y[1], acc_x + acc_w, acc_y[1] + acc_h], radius=8, fill=card_active_bg, outline=card_active_border, width=1)
            d.ellipse([acc_x + 16, acc_y[1] + 18, acc_x + 24, acc_y[1] + 26], fill=c_mint)
            d.text((acc_x + 32, acc_y[1] + 15), "Account 2 (Active P1)", font=f_body_bold, fill=c_zinc)
            d.text((acc_x + 32, acc_y[1] + 35), "Resumed with 100% Memory", font=f_mono, fill=c_mint)
            d.rounded_rectangle([acc_x + 32, acc_y[1] + 55, acc_x + 32 + 150, acc_y[1] + 61], radius=3, fill=(35, 40, 55))
            d.rounded_rectangle([acc_x + 32, acc_y[1] + 55, acc_x + 32 + 142, acc_y[1] + 61], radius=3, fill=c_mint)
            d.text((acc_x + 190, acc_y[1] + 50), "95%", font=f_mono, fill=c_mint)

        # Account 3 (Idle standby)
        d.rounded_rectangle([acc_x, acc_y[2], acc_x + acc_w, acc_y[2] + acc_h], radius=8, fill=card_bg, outline=card_border, width=1)
        d.ellipse([acc_x + 16, acc_y[2] + 18, acc_x + 24, acc_y[2] + 26], outline=c_dim, width=1)
        d.text((acc_x + 32, acc_y[2] + 15), "Account 3 (Standby P3)", font=f_body, fill=c_muted)
        d.text((acc_x + 32, acc_y[2] + 35), "backup@org.com", font=f_mono, fill=c_dim)
        d.rounded_rectangle([acc_x + 32, acc_y[2] + 55, acc_x + 32 + 150, acc_y[2] + 61], radius=3, fill=(35, 40, 55))
        d.rounded_rectangle([acc_x + 32, acc_y[2] + 55, acc_x + 32 + 150, acc_y[2] + 61], radius=3, fill=c_dim)
        d.text((acc_x + 190, acc_y[2] + 50), "100%", font=f_mono, fill=c_dim)

        # ----------------- Connection Lines (Accounts -> Hub) -----------------
        start_y = [acc_y[0] + acc_h // 2, acc_y[1] + acc_h // 2, acc_y[2] + acc_h // 2]
        hub_in_x = hub_x
        hub_in_y = hub_y + hub_h // 2

        for i in range(3):
            # Base wire
            is_active_wire = (i == 0 and phase == 1) or (i == 1 and phase == 4)
            wire_color = c_mint if is_active_wire else c_line_dim
            d.line([(acc_x + acc_w, start_y[i]), (hub_in_x, hub_in_y)], fill=wire_color, width=2 if is_active_wire else 1)

            # Animated pulse along active wire
            if is_active_wire:
                t = (f * 0.15) % 1.0
                px = (acc_x + acc_w) + t * (hub_in_x - (acc_x + acc_w))
                py = start_y[i] + t * (hub_in_y - start_y[i])
                d.ellipse([px - 4, py - 4, px + 4, py + 4], fill=c_mint)
                d.ellipse([px - 2, py - 2, px + 2, py + 2], fill=(255, 255, 255))

        # Phase 3: Transfer Packet between Account 1 & Account 2
        if phase == 3:
            t = (f - 25) / 10.0
            # Packet travels from Account 1 wire to Account 2
            d.rounded_rectangle([hub_x - 30, hub_y - 28, hub_x + 130, hub_y], radius=6, fill=(35, 30, 48), outline=c_accent, width=1)
            d.text((hub_x - 20, hub_y - 20), "⚡ Syncing: session.jsonl", font=f_mono, fill=c_accent)
            
            # Transfer pulse downward
            transfer_y = start_y[0] + t * (start_y[1] - start_y[0])
            d.ellipse([acc_x + acc_w + 15 - 4, transfer_y - 4, acc_x + acc_w + 15 + 4, transfer_y + 4], fill=c_accent)

        # ----------------- Center: Claude Pool Engine -----------------
        d.rounded_rectangle([hub_x, hub_y, hub_x + hub_w, hub_y + hub_h], radius=12, fill=(24, 27, 38), outline=c_accent, width=2)
        
        # Inner badge
        d.rounded_rectangle([hub_x + 15, hub_y + 16, hub_x + hub_w - 15, hub_y + 42], radius=6, fill=(32, 36, 52))
        d.text((hub_x + 35, hub_y + 22), "claude-pool", font=f_title_bold, fill=c_accent)
        
        # Engine modules inside
        d.text((hub_x + 20, hub_y + 58), "● Failover Router", font=f_mono, fill=c_mint if phase in [1, 4] else c_ochre)
        d.text((hub_x + 20, hub_y + 82), "● Session Mirror", font=f_mono, fill=c_mint)
        d.text((hub_x + 20, hub_y + 106), "● Quota Telemetry", font=f_mono, fill=c_accent)
        d.text((hub_x + 20, hub_y + 130), "● Auto Re-launcher", font=f_mono, fill=c_zinc)

        # Pulse ring on hub
        pulse_r = int(4 + (math.sin(f * 0.4) + 1) * 2)
        d.ellipse([hub_x + hub_w - 24 - pulse_r, hub_y + 28 - pulse_r, hub_x + hub_w - 24 + pulse_r, hub_y + 28 + pulse_r], fill=c_mint if phase in [1, 4] else c_ochre)

        # ----------------- Connection Line (Hub -> Continuous Session) -----------------
        hub_out_x = hub_x + hub_w
        hub_out_y = hub_y + hub_h // 2
        out_in_x = out_x
        out_in_y = out_y + out_h // 2

        # Active output stream
        d.line([(hub_out_x, hub_out_y), (out_in_x, out_in_y)], fill=c_mint, width=2)
        
        # Stream particle
        ot = (f * 0.2) % 1.0
        opx = hub_out_x + ot * (out_in_x - hub_out_x)
        opy = hub_out_y + ot * (out_in_y - hub_out_y)
        d.ellipse([opx - 4, opy - 4, opx + 4, opy + 4], fill=c_mint)
        d.ellipse([opx - 2, opy - 2, opx + 2, opy + 2], fill=(255, 255, 255))

        # ----------------- Right: Claude Code Continuous Session -----------------
        d.rounded_rectangle([out_x, out_y, out_x + out_w, out_y + out_h], radius=10, fill=card_bg, outline=card_active_border, width=1)
        d.text((out_x + 18, out_y + 18), "Claude Code Session", font=f_body_bold, fill=c_zinc)
        
        status_text = "● Stream Active (Account 1)" if phase == 1 else (
            "⚠️ Switching Account..." if phase in [2, 3] else "● Resumed on Account 2"
        )
        status_color = c_mint if phase in [1, 4] else c_ochre
        d.text((out_x + 18, out_y + 42), status_text, font=f_mono_bold, fill=status_color)

        # Pill badge: Zero Lost Context
        d.rounded_rectangle([out_x + 18, out_y + 70, out_x + out_w - 18, out_y + 96], radius=6, fill=(20, 32, 26), outline=(35, 75, 50), width=1)
        d.text((out_x + 26, out_y + 76), "✓ Zero Memory Loss", font=f_mono_bold, fill=c_mint)

        d.text((out_x + 18, out_y + 108), "Transcripts automatically synced", font=f_badge, fill=c_dim)

        # ----------------- Bottom Summary Banner -----------------
        d.rounded_rectangle([45, 360, W - 45, 396], radius=6, fill=(18, 20, 30), outline=(32, 35, 48), width=1)
        
        if phase == 1:
            msg = "Phase 1: Session running on Account 1 · Real-time quota depletion tracked"
            m_color = c_mint
        elif phase == 2:
            msg = "Phase 2: Account 1 reaches 5-hour Anthropic cap · claude-pool catches event"
            m_color = c_ochre
        elif phase == 3:
            msg = "Phase 3: Active session transcript (.jsonl) seamlessly mirrored to Account 2"
            m_color = c_accent
        else:
            msg = "Phase 4: Seamless resumption with claude --resume · Uninterrupted developer flow"
            m_color = c_mint

        d.text((60, 370), msg, font=f_mono, fill=m_color)

        # Convert to P-mode for compact GIF
        rgb = Image.new("RGB", im.size, bg_color)
        rgb.paste(im, mask=im.split()[3])
        frames.append(rgb.quantize(colors=128, method=Image.Quantize.MEDIANCUT))

    # Save animated GIF
    durations = [140] * total_frames
    # Pause longer on Phase 1, Phase 2, and Phase 4 for viewer comprehension
    for i in [14, 23, 47]:
        durations[i] = 1200

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
    create_pool_flow_gif()
