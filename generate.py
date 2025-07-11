from argparse import ArgumentParser
import json

import torch
import tiktoken

from model.language_model import LanguageModel

def generate_text(model, token_ids, max_new_tokens, context_length):
    """
    使用模型生成文本
    
    Args:
        model: 语言模型
        token_ids: 输入文本的 token ids 张量，形状为 (batch_size, num_tokens)
        max_new_tokens: 新生成的 token 最大数量
        context_length: 最大上下文长度
    """
    for _ in range(max_new_tokens):
        # 将当前文本截断至支持的长度。如果大模型仅支持5个词元，如果输入文本长度为10，则只有最后5个词元会被用于输入文本
        real_token_ids = token_ids[:, -context_length:]

        # no_grad 用于禁用梯度计算，只有在训练时才需要计算梯度来减小损失函数，禁用后可以加速计算减少内存占用
        with torch.no_grad():
            logits = model(real_token_ids)
        
        # 因为模型会为每个 token 生成一个 logits，而我们只需要最后一个 token 的 logits，所以需要将维度减少一个维度，
        # 使得形状从 (batch_size, num_tokens, vocab_size) 变为 (batch_size, vocab_size)
        logits = logits[:, -1, :]

        # 将 logits 分数转换为概率分布，不会改变输入顺序
        probabilities = torch.softmax(logits, dim=-1)

        # argmax 方法用于返回张量中每个元素的最大值的索引，
        # 这里返回的是概率最大的词元的 token id，形状为 (batch_size, 1)
        next_token_id = torch.argmax(probabilities, dim=-1, keepdim=True)

        # 将新生成的 token id 添加到文本末尾，继续下一个循环，生成下一个 token
        token_ids = torch.cat((token_ids, next_token_id), dim=-1)
    return token_ids


def main(config):
    """
    初始化大模型并执行文本生成

    Arguments:
        --config (str): 模型配置参数文件路径
    """
    # 加载编码器，默认为 gpt2
    tokenizer = tiktoken.get_encoding("gpt2")

    # 设置随机种子以保证结果可复现
    torch.manual_seed(123)    
    with open(config) as f:
        cfg = json.load(f)

    # 初始化模型
    model = LanguageModel(cfg)
    # 切换为推断模式，将禁用 dropout 等只在训练时使用的功能
    model.eval()

    # 交互式对话循环
    print("开始对话（输入'exit'退出）")
    while True:
        user_input = input("用户: ")
        if user_input.lower() == 'exit':
            break

        # 将用户输入的文本转换为 token id
        # unsqueeze 方法用于在张量维度上增加一个维度，这里在第一个维度上增加一个维度，使得输入的形状为 (1, num_tokens)
        # 这里使用 unsqueeze 方法是因为模型要求输入的形状为 (batch_size, num_tokens)
        token_ids = torch.tensor(tokenizer.encode(user_input)).unsqueeze(0)

        # 使用模型生成文本，输入输出均为 token id
        output_ids = generate_text(
            model=model,
            token_ids=token_ids,
            max_new_tokens=6,
            context_length=cfg["context_length"]
        )

        # 将 token id 转换为文本并打印
        # squeeze 方法用于在张量维度上减少一个维度，这里在第一个维度上减少一个维度，使得输出的形状为 (num_tokens)
        # 这里使用 squeeze 方法是因为模型输出的形状为 (batch_size, num_tokens)，而我们只需要一个文本，因此需要减少一个维度
        output_text = tokenizer.decode(output_ids.squeeze(0).tolist())
        print(f"模型: {output_text}\n")

if __name__ == "__main__":
    """
    命令行工具

    Arguments:
        --config (str): 模型配置参数文件路径
    """
    parser = ArgumentParser()
    parser.add_argument("--config", type=str, required=True)
    args = parser.parse_args()
    main(args.config)
