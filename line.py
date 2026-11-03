import argparse
import mimetypes
import os
import uuid
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv
from google.auth.exceptions import DefaultCredentialsError
from google.cloud import storage


load_dotenv(Path(__file__).with_name(".env"))


PROJECT_ID = "yannichang-linebot-2026"

BUCKET_NAME = (
    "yannichang-linebot-images-2026-310511"
)

MAX_SIZE_BYTES = 1 * 1024 * 1024


def validate_image(image_path: Path) -> str:
    """验证本机图片，返回 MIME 类型。"""
    if not image_path.is_file():
        raise FileNotFoundError(
            f"找不到图片：{image_path}"
        )

    mime_type, _ = mimetypes.guess_type(
        image_path.name
    )

    if mime_type not in {
        "image/jpeg",
        "image/png",
    }:
        raise ValueError(
            "只接受 JPEG 或 PNG 图片"
        )

    file_size = image_path.stat().st_size

    if file_size > MAX_SIZE_BYTES:
        raise ValueError(
            "图片超过 1 MB，不能同时作为 LINE 预览图"
        )

    return mime_type


def upload_image(
    image_path: Path,
    mime_type: str,
) -> str:
    """上传图片至 Google Cloud Storage。"""
    extension = (
        ".jpg"
        if mime_type == "image/jpeg"
        else ".png"
    )

    object_name = (
        f"line/photo-{uuid.uuid4().hex}{extension}"
    )

    client = storage.Client(
        project=PROJECT_ID,
    )

    bucket = client.bucket(BUCKET_NAME)
    blob = bucket.blob(object_name)

    blob.cache_control = "public,max-age=3600"

    print("[1/3] 上传图片至 Google Cloud Storage...")

    blob.upload_from_filename(
        str(image_path),
        content_type=mime_type,
    )

    encoded_object_name = quote(
        object_name,
        safe="/",
    )

    return (
        "https://storage.googleapis.com/"
        f"{BUCKET_NAME}/"
        f"{encoded_object_name}"
    )


def verify_image_url(image_url: str) -> None:
    """确认图片可由互联网公开读取。"""
    print("[2/3] 检查公开图片 URL...")

    response = requests.head(
        image_url,
        timeout=30,
    )

    response.raise_for_status()

    content_type = response.headers.get(
        "Content-Type",
        "",
    )

    if not content_type.startswith("image/"):
        raise RuntimeError(
            f"URL 返回的不是图片：{content_type}"
        )


def send_to_line(image_url: str) -> None:
    """透过 LINE Messaging API 发送图片。"""
    channel_access_token = os.environ.get(
        "LINE_CHANNEL_ACCESS_TOKEN"
    )

    line_user_id = os.environ.get(
        "LINE_USER_ID"
    )

    if not channel_access_token:
        raise RuntimeError(
            "尚未设置 LINE_CHANNEL_ACCESS_TOKEN"
        )

    if not line_user_id:
        raise RuntimeError(
            "尚未设置 LINE_USER_ID"
        )

    payload = {
        "to": line_user_id,
        "messages": [
            {
                "type": "image",
                "originalContentUrl": image_url,
                "previewImageUrl": image_url,
            }
        ],
    }

    headers = {
        "Authorization": (
            f"Bearer {channel_access_token}"
        ),
        "Content-Type": "application/json",
    }

    print("[3/3] 传送图片至 LINE...")

    response = requests.post(
        "https://api.line.me/v2/bot/message/push",
        headers=headers,
        json=payload,
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            "LINE API 错误："
            f"{response.status_code} "
            f"{response.text}"
        )


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "上传本机图片至 Google Cloud，"
            "然后传送至 LINE"
        )
    )

    parser.add_argument(
        "image",
        help="本机 JPEG 或 PNG 图片路径",
    )

    arguments = parser.parse_args()
    image_path = Path(arguments.image).resolve()

    try:
        mime_type = validate_image(image_path)

        image_url = upload_image(
            image_path,
            mime_type,
        )

        verify_image_url(image_url)
        send_to_line(image_url)

        print("图片已成功传送。")
        print(f"图片 URL：{image_url}")

    except DefaultCredentialsError:
        print(
            "执行失败：找不到 Google Cloud 凭证。\n"
            "请在 .env 设置：\n"
            "GOOGLE_APPLICATION_CREDENTIALS=C:\\\\path\\\\to\\\\service-account.json\n"
            "并确认该服务账号拥有目标 Storage bucket 的写入权限。"
        )
        raise SystemExit(1)
    except Exception as error:
        print(
            "执行失败："
            f"{type(error).__name__}: {error}"
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
