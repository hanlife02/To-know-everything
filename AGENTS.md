# Agent 工作规范：文档管理 (Document Management Rules)

在执行任何与文档相关的操作时，你**必须**严格遵守以下路径规范。**严禁**在当前工作目录下直接新建任何文档文件。

## 1. 目标路径定义
* **全局文档根目录**：`/Users/hanlife02/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ethan/Docs`
* **当前项目子目录**：提取当前工作目录的名称（如当前在 `~/Desktop/code/MyProject`，则名称为 `MyProject`），将其作为全局文档根目录下的子目录。
  * *示例*：如果当前工作目录名为 `Ethan`，则最终的目标操作路径为 `/Users/hanlife02/Library/Mobile Documents/iCloud~md~obsidian/Documents/Ethan/Docs/Ethan`。

## 2. 行为准则
当接收到创建、查找或更新文档的任务时，按以下逻辑执行：

1. **目录初始化**：在执行写入操作前，检查对应的项目子目录是否存在。如果不存在，**必须先自动创建该目录**。
2. **创建文档**：所有新文档必须且只能保存在计算出的目标项目子目录中。
3. **查找文档**：当需要读取或检索项目相关文档时，直接定位到对应的项目子目录中进行查找，忽略当前工作目录。

**【严格红线】**：绝对不允许污染当前工作目录的代码/工程环境，所有知识管理与文档沉淀必须被统一路由至上述指定的 Obsidian 文件夹内。、



**确保当前文件，即AGENTS.md被.gitignore追踪**