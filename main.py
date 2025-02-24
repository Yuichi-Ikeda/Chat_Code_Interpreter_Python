import os
import time
from openai import AzureOpenAI

FILE_FONT_PATH = ".\\input_files\\Font.zip"
FILE_EXCEL_PATH = ".\\input_files\\Excel.zip"

api_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("API_VERSION")
deployment_name = os.getenv("DEPLOYMENT_NAME")

try:
    # クライアントの初期化
    client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=api_endpoint)

    # FONT ファイルをアップロード
    file_font = client.files.create(file=open(FILE_FONT_PATH, "rb"), purpose='assistants')
    print(f"Font file uploaded successfully. File ID: {file_font.id}")

    # アシスタントを作成
    assistant = client.beta.assistants.create(
        name="AI Assistant for Excel File Analysis",
        model=deployment_name,
        instructions="You are an AI assistant that analyzes EXCEL files. Please answer user requests in Japanese.",
        tools=[{"type": "code_interpreter"}],
        tool_resources={"code_interpreter": {"file_ids": [file_font.id]}},
    )
    print(f"Assistant created successfully. Assistant ID: {assistant.id}\n")

    # EXCEL ファイルをアップロード
    file_excel = client.files.create(file=open(FILE_EXCEL_PATH, "rb"), purpose='assistants')
    print(f"Excel file uploaded successfully. File ID: {file_excel.id}")

    # スレッドを作成
    thread = client.beta.threads.create(
        messages=[
            {
                "role": "user",
                "content": "アップロードされた Font.zip と Excel.zip を /mnt/data/upload_files に展開してください。これらの ZIP ファイルには解析対象の EXCEL ファイルと日本語フォント NotoSansJP.ttf が含まれています。展開した先にある EXCEL ファイルをユーザーの指示に従い解析してください。EXCEL データからグラフやチャート画像を生成する場合、タイトル、軸項目、凡例等に NotoSansJP.ttf を利用してください。",
                "attachments":[
                    {
                    "file_id": file_font.id,
                    "file_id": file_excel.id,
                    "tools": [{"type": "code_interpreter"}]
                    }
                ]
            }
        ]
    )
    print("Chat session started. Type 'exit' to end the session.")

    # チャットループ
    while True:
        # ユーザー入力を取得
        user_input = input("\nUser: ")
        
        # 終了コマンドの処理
        if user_input.lower() == "exit":
            print("Ending session...")
            break
        
        # ユーザーのメッセージを送信
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # アシスタントの応答を取得
        run = client.beta.threads.runs.create(
            thread_id=thread.id, 
            assistant_id=assistant.id,
        )

        print("\nWaiting for response...")
        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            messages = client.beta.threads.messages.list(thread_id=thread.id)

            if run.status == "completed":
                print(f"\nRun status: {run.status}")
                for message in messages:
                    print(f"{message.content}")

                print("\nAssistant:")
                for content_block in messages.data[0].content:
                    if content_block.type == "text":
                        print(content_block.text.value)
                    elif content_block.type == "image_file":
                        file_id = content_block.image_file.file_id
                        print(f"[Image file received: {file_id}]")

                        try:
                            file = client.files.content(file_id)
                            file_data = file.read()
                            with open(f".\\output_images\\{file_id}.png", "wb") as f:
                                f.write(file_data)
                            print(f"File saved as '{file_id}.png'")
                        except Exception as e:
                            print(f"Error retrieving image: {e}")
                    else:
                        print(f"Unhandled content type: {content_block.type}")
                break

            elif run.status in ["queued", "in_progress"]:
                print(f"\nRun status: {run.status}")
                for message in messages:
                    print(f"{message.content}")
                time.sleep(5)

            else:
                print(f"Run status: {run.status}")
                if run.status == "failed":
                    print(f"Error Code: {run.last_error.code}, Message: {run.last_error.message}")
                break

    # スレッドを削除
    client.beta.threads.delete(thread.id)
    print("Thread deleted successfully.")

    # EXCEL ファイルを削除
    client.files.delete(file_excel.id)
    print("Excel file deleted successfully.")

    # アシスタントを削除
    client.beta.assistants.delete(assistant.id)
    print("Assistant deleted successfully.")

    # FONT ファイルを削除
    client.files.delete(file_font.id)
    print("Font file deleted successfully.")

except Exception as e:
    print(f"An error occurred: {e}")
