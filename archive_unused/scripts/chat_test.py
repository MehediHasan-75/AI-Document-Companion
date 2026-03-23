# # from langchain_ollama import ChatOllama
# # from langchain_core.messages import HumanMessage

# # # # Create LLM instance
# # llm = ChatOllama(
# #     model="deepseek-r1:8b",
# #     base_url="http://localhost:11434",
# #     temperature=0.7
# # )

# # # # Send message
# # # response = llm.invoke(
# # #     [HumanMessage(content="who are you?")]
# # # )

# # # print(response.content)

# # import base64

# # # Load an image and convert to base64
# # with open("test_image.png", "rb") as f:
# #     image_bytes = f.read()
# # image_b64 = base64.b64encode(image_bytes).decode("utf-8")

# # # Prompt for image
# # prompt_text = "Describe this image in detail, focusing on important elements."

# # response = llm.invoke([
# #     HumanMessage(
# #         content="Describe this image in detail.",
# #         additional_kwargs={"image_url": f"data:image/jpeg;base64,{image_b64}"}
# #     )
# # ])

# # print("Image response:\n", response.content)

# from langchain_ollama import ChatOllama
# from langchain_core.messages import HumanMessage
# import base64

# # Load image
# with open("test_image1.png", "rb") as f:
#     image_bytes = f.read()
# image_b64 = base64.b64encode(image_bytes).decode("utf-8")

# llm = ChatOllama(
#     model="llava",  # or deepseek-r1:8b
#     base_url="http://localhost:11434",
#     temperature=0.7
# )

# response = llm.invoke([
#     HumanMessage(
#         content="Describe this image in detail.",
#         additional_kwargs={"image_url": f"data:image/jpeg;base64,{image_b64}"}
#     )
# ])

# print(response.content)

from langchain_ollama import ChatOllama
from langchain_core.messages import HumanMessage
import base64

with open("test_image1.png", "rb") as f:
    image_b64 = base64.b64encode(f.read()).decode("utf-8")

llm = ChatOllama(model="llava", base_url="http://localhost:11434", temperature=0.7)

response = llm.invoke([
    HumanMessage(content=[
        {
            "type": "image_url",
            "image_url": f"data:image/png;base64,{image_b64}"
        },
        {
            "type": "text",
            "text": "Describe this image in detail."
        }
    ])
])

print(response.content)