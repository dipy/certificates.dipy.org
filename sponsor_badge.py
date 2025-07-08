#!/usr/bin/env python3
"""
Generate dynamic sponsor badges for GitHub profiles and READMEs.
This creates SVG badges that can be embedded in GitHub.
"""

import os
import json
from datetime import datetime
from typing import List, Dict, Any

# Badge templates
SPONSOR_BADGE_TEMPLATE = """
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="28" viewBox="0 0 200 28">
  <linearGradient id="b" x2="0" y2="100%">
    <stop offset="0" stop-color="#bbb" stop-opacity=".1"/>
    <stop offset="1" stop-opacity=".1"/>
  </linearGradient>
  <mask id="a">
    <rect width="200" height="28" rx="5" fill="#fff"/>
  </mask>
  <g mask="url(#a)">
    <path fill="#555" d="M0 0h32v28H0z"/>
    <path fill="#007ec6" d="M32 0h168v28H32z"/>
    <path fill="url(#b)" d="M0 0h200v28H0z"/>
  </g>
  <g fill="#fff" text-anchor="middle" font-family="DejaVu Sans,Verdana,Geneva,sans-serif" font-size="11">
    <text x="16" y="18" fill="#010101" fill-opacity=".3">sponsor</text>
    <text x="16" y="17">sponsor</text>
    <text x="116" y="18" fill="#010101" fill-opacity=".3">{count}</text>
    <text x="116" y="17">{count}</text>
  </g>
</svg>
"""

SPONSOR_LIST_TEMPLATE = """
# 🤝 DIPY Sponsors

Thank you to our amazing sponsors who support DIPY development!

## Current Sponsors

{sponsor_list}

## Become a Sponsor

Support DIPY development by becoming a sponsor:
- **Individual Plan**: $49 - Perfect for individual developers
- **Team Plan**: $350 - Great for teams and organizations

[Sponsor DIPY →](https://your-domain.com/services/sponsors)

---

*Last updated: {last_updated}*
"""

def generate_sponsor_badge(sponsor_count: int) -> str:
    """Generate an SVG badge showing sponsor count."""
    return SPONSOR_BADGE_TEMPLATE.format(count=sponsor_count)

def generate_sponsor_list(sponsors: List[Dict[str, Any]]) -> str:
    """Generate a markdown list of sponsors."""
    if not sponsors:
        return "No sponsors yet. Be the first! 🎉"
    
    sponsor_lines = []
    for sponsor in sponsors:
        username = sponsor.get('github_username', 'Unknown')
        plan_type = sponsor.get('plan_type', 'individual').title()
        avatar_url = sponsor.get('github_avatar_url', '')
        
        if avatar_url:
            sponsor_lines.append(f"- <img src=\"{avatar_url}\" width=\"20\" height=\"20\" alt=\"{username}\"> **[{username}](https://github.com/{username})** - {plan_type} Plan")
        else:
            sponsor_lines.append(f"- **[{username}](https://github.com/{username})** - {plan_type} Plan")
    
    return "\n".join(sponsor_lines)

def create_sponsor_readme(sponsors: List[Dict[str, Any]], output_file: str = "SPONSORS.md"):
    """Create a SPONSORS.md file for GitHub."""
    sponsor_list = generate_sponsor_list(sponsors)
    sponsor_count = len(sponsors)
    
    content = SPONSOR_LIST_TEMPLATE.format(
        sponsor_list=sponsor_list,
        last_updated=datetime.now().strftime("%Y-%m-%d %H:%M UTC")
    )
    
    with open(output_file, 'w') as f:
        f.write(content)
    
    print(f"✅ Created {output_file} with {sponsor_count} sponsors")

def create_sponsor_badge_file(sponsor_count: int, output_file: str = "sponsor-badge.svg"):
    """Create an SVG badge file."""
    badge_svg = generate_sponsor_badge(sponsor_count)
    
    with open(output_file, 'w') as f:
        f.write(badge_svg)
    
    print(f"✅ Created {output_file} with {sponsor_count} sponsors")

def generate_github_profile_sponsors(sponsors: List[Dict[str, Any]]) -> str:
    """Generate sponsor section for GitHub profile README."""
    if not sponsors:
        return ""
    
    sponsor_lines = []
    for sponsor in sponsors[:5]:  # Show top 5 sponsors
        username = sponsor.get('github_username', 'Unknown')
        avatar_url = sponsor.get('github_avatar_url', '')
        
        if avatar_url:
            sponsor_lines.append(f"<a href=\"https://github.com/{username}\"><img src=\"{avatar_url}\" width=\"50\" height=\"50\" alt=\"{username}\" title=\"{username}\"></a>")
        else:
            sponsor_lines.append(f"<a href=\"https://github.com/{username}\">@{username}</a>")
    
    return f"""
## 🤝 Sponsors

Thank you to our sponsors!

{''.join(sponsor_lines)}

[Sponsor DIPY →](https://your-domain.com/services/sponsors)
"""

if __name__ == "__main__":
    # Example usage
    sample_sponsors = [
        {
            "github_username": "user1",
            "github_avatar_url": "https://avatars.githubusercontent.com/u/123?v=4",
            "plan_type": "individual"
        },
        {
            "github_username": "user2", 
            "github_avatar_url": "https://avatars.githubusercontent.com/u/456?v=4",
            "plan_type": "team"
        }
    ]
    
    create_sponsor_readme(sample_sponsors)
    create_sponsor_badge_file(len(sample_sponsors))
    print(generate_github_profile_sponsors(sample_sponsors)) 