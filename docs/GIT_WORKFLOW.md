# GitHub 协作操作手册

## 一、谁创建和提交仓库

组长创建 GitHub 仓库，例如 `xinghe-commerce-course-project`，然后在 Settings → Collaborators 中邀请另外四名成员。**每位成员必须用自己的 GitHub 账号提交本人负责的代码**；组长不能替其他人提交，否则无法证明个人贡献。

组长初始化：

```bash
git init
git add .
git commit -m "chore: initialize multi-role commerce project"
git branch -M main
git remote add origin https://github.com/组长账号/xinghe-commerce-course-project.git
git push -u origin main

git checkout -b develop
git push -u origin develop
```

在 GitHub 开启分支保护：

- `main`：禁止直接 push，必须 Pull Request，至少 1 人审批，要求测试通过。
- `develop`：禁止 force push，建议 Pull Request。

## 二、分支分配

| 人员 | 分支 |
|---|---|
| 组长 | `feature/core-workflow` |
| 成员A | `feature/user-pwa` |
| 成员B | `feature/merchant-console` |
| 成员C | `feature/admin-rbac` |
| 成员D | `feature/miniprogram-testing` |

每位成员首次操作：

```bash
git clone https://github.com/组长账号/xinghe-commerce-course-project.git
cd xinghe-commerce-course-project
git checkout develop
git pull origin develop
git checkout -b feature/自己的分支
```

## 三、日常提交

不要一次完成全部内容后只提交一次。至少在三个不同时间点提交：功能、修复、测试/文档各一次。

```bash
git status
git add app/routers/merchant.py app/templates/merchant/
git commit -m "feat(merchant): add shipping workflow"
git push -u origin feature/merchant-console
```

推荐提交前缀：

- `feat` 新功能
- `fix` Bug 修复
- `test` 测试
- `docs` 文档
- `refactor` 重构但不改变行为
- `chore` 工程配置

禁止使用 `update`、`修改一下`、`final` 这类无法说明内容的提交信息。

## 四、同步 develop，减少冲突

每天开始工作前：

```bash
git checkout develop
git pull origin develop
git checkout feature/自己的分支
git merge develop
```

发生冲突后，不要直接删除别人的代码。逐个文件检查 `<<<<<<<`、`=======`、`>>>>>>>`，保留正确逻辑，然后：

```bash
git add 冲突文件
git commit -m "merge: resolve develop conflicts"
git push
```

## 五、Pull Request 流程

成员完成一小块可测试功能后，把自己的分支推送到 GitHub，发起 `feature/... → develop` 的 Pull Request。PR 描述必须包括：

1. 完成了什么业务流程；
2. 修改了哪些接口和数据库字段；
3. 手工测试步骤；
4. 自动测试结果；
5. 页面截图；
6. 已知限制。

组长审核：

```bash
git fetch origin
git checkout 对方分支
git pull
pip install -r requirements-dev.txt
pytest
python run.py
```

确认后使用 **Create a merge commit** 或 `--no-ff` 合并，避免把所有成员提交压成一个提交，便于截图证明贡献。

## 六、最终发布

所有功能合并到 `develop` 后：

```bash
git checkout develop
git pull origin develop
pytest

git checkout main
git pull origin main
git merge --no-ff develop -m "release: complete course project v1.0.0"
git tag -a v1.0.0 -m "course submission release"
git push origin main --tags
```

GitHub Releases 新建 `v1.0.0`，附：运行说明、演示账号、测试结果和已知限制。

## 七、个人报告中的 Git 证据

每人至少截取三个不同时间点、不同内容的提交。建议执行：

```bash
git log --author="自己的 GitHub 邮箱" --date=local --pretty=format:"%h | %ad | %s" --stat
```

截图必须能看见：提交哈希、日期时间、提交说明、修改文件。再补一张本人 Pull Request 页面和一次 Code Review 评论截图，团队合作部分会更有说服力。
