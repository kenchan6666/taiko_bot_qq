"""
解析HTML难度表文件，提取歌曲信息并转换为JSON格式。

从HTML中提取：
- 歌曲名称（从<a href>标签中）
- 星数（★×10）
- 真实难度（10.2, 10.3等）
- BPM（如果存在）
- 流派（genre_pops, genre_anime等）

难度分级：
- 11.3以上为超级难
- 11.0以上为很难
- 10.7开始为难
- 10.4以上中等
"""
import json
import re
from pathlib import Path
from typing import Optional


def extract_song_info(html_content: str) -> list[dict]:
    """
    从HTML内容中提取歌曲信息。
    
    Args:
        html_content: HTML文件内容
        
    Returns:
        歌曲信息列表，每个字典包含：
        - name: 歌曲名称
        - stars: 星数（如10）
        - real_difficulty: 真实难度（如10.2）
        - difficulty_category: 难度分级（超级难、很难、难、中等、其他）
        - bpm: BPM（如果存在）
        - genre: 流派（如果存在）
        - url: 歌曲链接（如果存在）
    """
    songs = []
    
    # 匹配每个歌曲的div块
    # 每个歌曲在一个 <div class="table table_grid_difficulty..."> 中
    song_pattern = r'<div class="table table_grid_difficulty[^"]*"[^>]*data-value="([\d.]+)"[^>]*>.*?</div>\s*</div>'
    
    # 更精确的模式：匹配包含data-value的div及其内部内容
    div_pattern = r'<div class="table table_grid_difficulty[^"]*"[^>]*data-value="([\d.]+)"[^>]*>(.*?)</div>\s*</div>'
    
    matches = re.finditer(div_pattern, html_content, re.DOTALL)
    
    for match in matches:
        real_difficulty_str = match.group(1)
        content = match.group(2)
        
        try:
            real_difficulty = float(real_difficulty_str)
        except ValueError:
            continue
        
        # 提取星数（★×10）
        star_match = re.search(r'★×(\d+)', content)
        stars = int(star_match.group(1)) if star_match else None
        
        # 提取歌曲名称和链接
        name_match = re.search(r'<a href="([^"]+)"[^>]*>([^<]+)</a>', content)
        if not name_match:
            continue
        
        url = name_match.group(1)
        name = name_match.group(2).strip()
        
        # 提取BPM
        bpm_match = re.search(r'<span class="bpm_base">(\d+)', content)
        bpm = int(bpm_match.group(1)) if bpm_match else None
        
        # 提取流派（从class属性中）
        genre_match = re.search(r'genre_(\w+)', content)
        genre = genre_match.group(1) if genre_match else None
        
        # 确定难度分级
        if real_difficulty >= 11.3:
            difficulty_category = "超级难"
        elif real_difficulty >= 11.0:
            difficulty_category = "很难"
        elif real_difficulty >= 10.7:
            difficulty_category = "难"
        elif real_difficulty >= 10.4:
            difficulty_category = "中等"
        else:
            difficulty_category = "其他"
        
        songs.append({
            "name": name,
            "stars": stars,
            "real_difficulty": real_difficulty,
            "difficulty_category": difficulty_category,
            "bpm": bpm,
            "genre": genre,
            "url": url,
        })
    
    return songs


def parse_difficulty_table(input_file: str, output_file: str) -> None:
    """
    解析难度表HTML文件并保存为JSON。
    
    Args:
        input_file: 输入的HTML文件路径
        output_file: 输出的JSON文件路径
    """
    input_path = Path(input_file)
    if not input_path.exists():
        raise FileNotFoundError(f"输入文件不存在: {input_file}")
    
    print(f"正在读取文件: {input_file}")
    with open(input_path, 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    print("正在解析歌曲信息...")
    songs = extract_song_info(html_content)
    
    print(f"共提取到 {len(songs)} 首歌曲")
    
    # 按难度排序（降序）
    songs.sort(key=lambda x: x['real_difficulty'], reverse=True)
    
    # 统计信息
    difficulty_stats = {}
    for song in songs:
        category = song['difficulty_category']
        difficulty_stats[category] = difficulty_stats.get(category, 0) + 1
    
    print(f"\n难度统计:")
    for category, count in sorted(difficulty_stats.items(), key=lambda x: x[1], reverse=True):
        print(f"  {category}: {count}首")
    
    # 保存为JSON
    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    output_data = {
        "total_songs": len(songs),
        "difficulty_stats": difficulty_stats,
        "songs": songs,
    }
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n已保存到: {output_file}")
    
    # 显示前10首最难的歌曲（使用safe打印避免编码错误）
    print(f"\n前10首最难的歌曲:")
    for i, song in enumerate(songs[:10], 1):
        try:
            name = song['name'].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            category = song['difficulty_category'].encode('utf-8', errors='ignore').decode('utf-8', errors='ignore')
            print(f"  {i}. {name} - 难度: {song['real_difficulty']} ({category})")
        except Exception:
            print(f"  {i}. [歌曲名编码错误] - 难度: {song['real_difficulty']} ({song['difficulty_category']})")


if __name__ == "__main__":
    # 文件路径
    input_file = "スコア難易度表 -太鼓の達人 譜面とかデータベース-.txt"
    output_file = "data/song_difficulty_database.json"
    
    try:
        parse_difficulty_table(input_file, output_file)
        print("\n解析完成！")
    except Exception as e:
        print(f"错误: {e}")
        import traceback
        traceback.print_exc()
