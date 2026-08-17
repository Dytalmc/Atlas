#!/usr/bin/env python3
"""Fix chat UI: remove sender names, increase padding, update labels."""

with open('atlas/ui.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Make replacements
replacements = [
    ("Hello — I'm Gemini 2.5 Flash.", "Hello — I'm your AI assistant."),
    ('name = "YOU" if is_user else "GEMINI 2.5 FLASH"\n            safe_message = html.escape(message).replace("\\n", "<br>")\n            bubbles.append(\n                f"<div style=\'margin:10px 0; text-align:{alignment};\'>"\n                f"<span style=\'display:inline-block; max-width:82%; text-align:left; background:{background}; "\n                "border-radius:13px; padding:10px 13px; color:#f3f6ff; line-height:1.5;\'>"\n                f"<span style=\'font-size:10px; font-weight:700; letter-spacing:1px; color:#c9d3ef\'>{name}</span><br>{safe_message}"', 'safe_message = html.escape(message).replace("\\n", "<br>")\n            bubbles.append(\n                f"<div style=\'margin:10px 0; text-align:{alignment};\'>"\n                f"<span style=\'display:inline-block; max-width:82%; text-align:left; background:{background}; "\n                "border-radius:13px; padding:20px; color:#f3f6ff; line-height:1.5;\'>\n                f"{safe_message}"'),
    ('("◌  Chat", "Chat with Gemini 2.5 Flash using local Atlas memory")', '("◌  Chat", "Chat with any Gemini model using local Atlas memory")'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"✓ Replaced chunk")
    else:
        print(f"✗ Not found: {old[:60]}...")

# Write back
with open('atlas/ui.py', 'w', encoding='utf-8') as f:
    f.write(content)

print("\n✓ Chat UI changes applied!")
