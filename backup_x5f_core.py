import requests, re, time, os
from datetime import datetime
import pandas as pd

BASE_CHAT = "https://pages.fm/api/v1"
BASE_POS = "https://pos.pages.fm/api/v1"

def get_pages(chat_token):
    url = f"{BASE_CHAT}/pages?access_token={chat_token}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_conversations(chat_token, page_id, page=1, limit=50):
    url = f"{BASE_CHAT}/pages/{page_id}/conversations?access_token={chat_token}&page={page}&limit={limit}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def get_messages(chat_token, page_id, conv_id, limit=100):
    url = f"{BASE_CHAT}/pages/{page_id}/conversations/{conv_id}/messages?access_token={chat_token}&limit={limit}"
    r = requests.get(url, timeout=20)
    r.raise_for_status()
    return r.json()

def backup_all(chat_token, pos_api_key=None):
    all_data = []
    pages_data = get_pages(chat_token)
    pages = pages_data.get('categorized', {}).get('activated', []) or pages_data.get('pages', [])
    print(f"Tìm thấy {len(pages)} page")
    
    for p in pages:
        page_id = p.get('id')
        page_name = p.get('name','')
        platform = p.get('platform','')
        print(f"-> Quét page: {page_name} ({platform}) - {page_id}")
        page_num = 1
        while True:
            try:
                convs = get_conversations(chat_token, page_id, page_num)
                items = convs.get('conversations', []) or convs.get('data', []) or []
                if not items:
                    break
                for c in items:
                    conv_id = c.get('id') or c.get('conversation_id')
                    customer = c.get('customer', {}) or {}
                    username = c.get('username','') or customer.get('username','')
                    display_name = customer.get('name','') or c.get('name','') or ''
                    # Format y het Pancake: id - ten
                    full_name = f"{username} - {display_name}" if username and display_name else (display_name or username or "Khách lạ")
                    
                    # Lấy tin nhắn cuối
                    last_msg_text = c.get('snippet','') or c.get('last_message','') or ''
                    phone_in_snippet = ""
                    try:
                        # thử lấy thêm messages để trích SĐT, địa chỉ
                        msgs = get_messages(chat_token, page_id, conv_id, limit=20)
                        messages = msgs.get('messages', []) or []
                        if messages:
                            # ghép 5 tin gần nhất
                            combined = " ".join([m.get('message','') or '' for m in messages[:5]])
                            last_msg_text = combined
                    except Exception as e:
                        print(f"   Lỗi lấy messages {conv_id}: {e}")
                    
                    # Trích SĐT, mã đơn kiểu A38-092
                    phones = re.findall(r'0\d{9,10}', last_msg_text)
                    ma_dons = re.findall(r'[A-Z]{1,3}\d{1,3}-\d{1,4}', last_msg_text)
                    
                    all_data.append({
                        "thoi_gian_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "page_name": page_name,
                        "platform": platform,
                        "page_id": page_id,
                        "conversation_id": conv_id,
                        "id_tiktok": username,
                        "ten_tiktok": display_name,
                        "ten_hien_thi_y_het_pancake": full_name,
                        "ma_don": ", ".join(ma_dons),
                        "sdt_trong_tin_nhan": ", ".join(phones),
                        "sdt_khach": customer.get('phone',''),
                        "dia_chi": customer.get('address',''),
                        "tin_nhan_cuoi": last_msg_text[:500],
                        "trang_thai": c.get('status',''),
                        "so_tin_chua_doc": c.get('unread_count',0)
                    })
                if len(items) < 50:
                    break
                page_num += 1
                time.sleep(0.8)
            except Exception as e:
                print(f"Lỗi page {page_id} trang {page_num}: {e}")
                break
    
    # Lưu ra Excel
    if all_data:
        df = pd.DataFrame(all_data)
        filename = f"backup_pancake_{datetime.now().strftime('%Y%m%d_%H%M')}.xlsx"
        df.to_excel(filename, index=False)
        print(f"Đã lưu {len(df)} dòng vào {filename}")
        # Lưu bản mới nhất ghi đè để app clone đọc
        df.to_excel("backup_latest.xlsx", index=False)
        df.to_json("backup_latest.json", orient="records", force_ascii=False, indent=2)
        return filename, len(df)
    else:
        print("Không có dữ liệu")
        return None, 0

if __name__ == "__main__":
    import dotenv
    dotenv.load_dotenv()
    chat_token = os.getenv("PANCAKE_CHAT_TOKEN")
    pos_key = os.getenv("PANCAKE_POS_API_KEY")
    if not chat_token:
        print("Chưa có PANCAKE_CHAT_TOKEN trong .env")
    else:
        backup_all(chat_token, pos_key)
