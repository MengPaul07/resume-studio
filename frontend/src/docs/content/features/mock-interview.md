---
title: Mock Interview 模拟面试
description: 从面试设置到复盘报告，完整练习技术、项目和行为面试。
category: features
order: 23
---

# Mock Interview 模拟面试

模拟面试会根据职位、级别、方向和语言生成面试官配置。面试过程中，用户可以在聊天、代码编辑器和笔记面板之间切换。

## 面试设置

可配置公司类型、岗位、职级、面试风格、深度、轮数、语言以及算法、系统设计、项目和行为问题的权重。自定义偏好限制为短文本，避免把无关指令塞进系统提示。

## 进行中

面试官通过 Agent 工具决定下一题；遇到编程题时，把题目和 starter code 发送到代码面板。Enter 发送答案，Shift+Enter 换行，Ctrl+Enter 提交代码。

面试状态保存在浏览器，服务端会话用于当前对话。关闭页面后可以继续未完成会话，也可以丢弃后重新开始。

## 复盘

结束面试后生成报告，包含总评、逐题反馈、优势、风险和下一步练习。Review Mode 会切换到教练视角，允许用户针对某一题重新演练。

## 相关 API

面试复用 v3 session/turn 通道；前端以 `start_interview`、`ask_question`、`ask_coding_question` 和 `end_interview` 工具事件驱动 UI。
