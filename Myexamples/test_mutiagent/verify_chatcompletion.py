#!/usr/bin/env python3
"""
验证 ChatCompletion 对象的结构和提取方法
"""

# 模拟 ChatCompletion 对象的结构（基于用户日志）
class ChatCompletionMessage:
    def __init__(self, content):
        self.content = content

class Choice:
    def __init__(self, message, finish_reason='stop', index=0):
        self.message = message
        self.finish_reason = finish_reason
        self.index = index
        self.logprobs = None

class ChatCompletion:
    def __init__(self, id, choices):
        self.id = id
        self.choices = choices
    
    def __repr__(self):
        return f"ChatCompletion(id={repr(self.id)}, choices={self.choices})"

# 创建模拟的 ChatCompletion 对象
test_content = "# Literature Review: Test Content\n\nThis is a test."
message = ChatCompletionMessage(content=test_content)
choice = Choice(message=message)
completion = ChatCompletion(id='test-id-123', choices=[choice])

print("=" * 80)
print("1. ChatCompletion 对象结构验证")
print("=" * 80)
print(f"对象类型: {type(completion)}")
print(f"对象表示: {completion}")
print()

print("=" * 80)
print("2. 检查对象属性")
print("=" * 80)
print(f"hasattr(completion, 'choices'): {hasattr(completion, 'choices')}")
print(f"completion.choices: {completion.choices}")
print(f"len(completion.choices): {len(completion.choices)}")
print()

print("=" * 80)
print("3. 提取内容的方法验证")
print("=" * 80)

# 方法 1：我的提取方法
if hasattr(completion, 'choices') and completion.choices:
    extracted_content = completion.choices[0].message.content
    print(f"✅ 提取成功!")
    print(f"提取的内容: {extracted_content}")
    print(f"内容类型: {type(extracted_content)}")
    print(f"内容长度: {len(extracted_content)} 字符")
else:
    print(f"❌ 提取失败")

print()

print("=" * 80)
print("4. 与字符串化对比")
print("=" * 80)
str_version = str(completion)
print(f"str(completion) 长度: {len(str_version)} 字符")
print(f"提取内容长度: {len(extracted_content)} 字符")
print(f"是否相同: {str_version == extracted_content}")
print()
print(f"str(completion) 前100字符:")
print(f"{str_version[:100]}")
print()
print(f"提取内容前100字符:")
print(f"{extracted_content[:100]}")

print()
print("=" * 80)
print("5. 结论")
print("=" * 80)
if extracted_content == test_content:
    print("✅ 提取方法正确: choices[0].message.content 能正确获取纯文本")
    print(f"✅ 避免了将对象转为字符串表示")
else:
    print("❌ 提取方法有问题")
