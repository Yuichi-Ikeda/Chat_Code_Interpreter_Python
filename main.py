import os
import time
from openai import AzureOpenAI

FILE_PATH = ".\\input_files\\Data.zip"

api_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
api_key = os.getenv("AZURE_OPENAI_API_KEY")
api_version = os.getenv("API_VERSION")
deployment_name = os.getenv("DEPLOYMENT_NAME")

try:
    client = AzureOpenAI(api_key=api_key, api_version=api_version, azure_endpoint=api_endpoint)
    # ファイルをアップロード
    file = client.files.create(file=open(FILE_PATH, "rb"), purpose='assistants')
    print(f"File uploaded successfully. File ID: {file.id}", flush=True)

    # アシスタントを作成
    assistant = client.beta.assistants.create(
        name="AI assistant",
        model=deployment_name,
        instructions="You are an AI assistant that analyzes uploaded files and answers user questions interactively. Please answer in Japanese.",
        tools=[{"type": "code_interpreter"}],
        tool_resources={"code_interpreter": {"file_ids": [file.id]}},
    )
    print(f"Assistant created successfully. Assistant ID: {assistant.id}")

    # スレッドを作成
    thread = client.beta.threads.create()
    print("Chat session started. Type 'exit' to end the session.")

    while True:
        # ユーザー入力を取得
        user_input = input("\nUser: ")
        
        if user_input.lower() == "exit":
            print("Ending session...")
            break
        
        # ユーザーのメッセージを送信
        message = client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=user_input
        )

        # アシスタントの応答を取得
        run = client.beta.threads.runs.create(
            thread_id=thread.id, 
            assistant_id=assistant.id,
            instructions="Please use the NotoSansJP.ttf font included in the ZIP file when writing titles, labels and legends on chart image.",
        )

        print("\nWaiting for response...")
        while True:
            run = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)

            if run.status == "completed":
                messages = client.beta.threads.messages.list(thread_id=thread.id)
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

            elif run.status == "requires_action":
                print("Requires action, handling function calling.")
                pass  # 追加の処理が必要な場合ここに書く

            elif run.status in ["expired", "failed", "cancelled"]:
                print(f"Run status: {run.status}")
                if run.status == "failed":
                    print(f"Error Code: {run.last_error.code}, Message: {run.last_error.message}")
                break

            else:
                print(f"Run status: {run.status}")
                time.sleep(5)

    # スレッドを削除
    client.beta.threads.delete(thread.id)
    print("Thread deleted successfully.")

    # アシスタントを削除
    client.beta.assistants.delete(assistant.id)
    print("Assistant deleted successfully.")

except Exception as e:
    print(f"An error occurred: {e}")
