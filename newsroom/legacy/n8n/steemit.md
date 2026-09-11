

## **n8n 工作流 JSON 代码生成与使用指南**

根据您提供的详细需求，以下是为“Hugo 文章自动发布到 Steemit”工作流设计的 n8n JSON 代码。

**重要提示：**

1.  **Steemit 中间服务是必须的。** 请确保您已部署并运行一个能够接收 n8n 请求并使用 `dsteem` 或其他 Steemit SDK 发布文章的服务（参照之前提供的 Node.js 示例）。**您需要将该服务的可访问 URL (例如 `http://your-server-ip:3000/publish-steemit`) 替换到工作流中的相应位置。**
2.  **创建 Steemit Credential：** 在 n8n 中创建一个新的 Credential，类型选择 `Generic Credential`，命名为 `SteemitPostingKey`。在其中添加一个字段，键为 `postingKey`，值为您的 Steemit Posting Key。
3.  **安装依赖 (针对中间服务)：** 确保您的中间服务运行环境中安装了 `express` 和 `dsteem` (或您选择的对应语言的 Steem SDK)。

### **工作流设计概述**

这个 n8n 工作流将包括以下主要步骤：

1.  **定时触发：** 每天固定时间触发。
2.  **获取 RSS Feed：** 从 `https://www.neican.ai/newspaper/index.xml` 获取最新文章列表。
3.  **获取上次发布状态：** 从 n8n 的内部存储（或者可以配置为文件、数据库等）获取上次成功发布的文章 ID/permlink。
4.  **比较与过滤：** 判断 RSS Feed 中的最新文章是否是新的或已更新，如果是则继续处理。
5.  **获取 Markdown 文件：** 根据 RSS Feed 中提取的链接，构建 GitHub raw URL，并下载 Markdown 文件内容。
6.  **解析 Markdown：** 分离 Front Matter 和文章正文。
7.  **准备 Steemit 数据：**
    *   提取标题 (`title`)。
    *   处理标签 (`tags`)，限制为最多5个。
    *   生成 Steemit `permlink` (优先使用 Front Matter 中的 `slug`/`permlink`，否则根据标题生成)。
    *   准备 Steemit 发布所需的其他数据。
8.  **发布到 Steemit：** 调用您的中间服务，发送 Steemit 发布请求。
9.  **更新发布状态：** 记录当前成功发布的文章 ID/permlink，以供下次执行时使用。
10. **错误处理：** 如果任何步骤失败，捕获错误并可配置发送通知。

### **n8n 工作流 JSON 代码**

```json
{
  "nodes": [
    {
      "parameters": {
        "rule": {
          "interval": [
            {
              "triggerAt": "09:00",
              "type": "everyDay"
            }
          ]
        }
      },
      "name": "Daily Trigger (09:00 AM)",
      "type": "n8n-nodes-base.cron",
      "typeVersion": 1,
      "position": [
        280,
        180
      ]
    },
    {
      "parameters": {
        "url": "https://www.neican.ai/newspaper/index.xml",
        "options": {}
      },
      "name": "Get RSS Feed",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [
        500,
        180
      ]
    },
    {
      "parameters": {
        "operation": "getItem",
        "key": "last_published_permlink",
        "valueFormat": "string"
      },
      "name": "Get Last Published Permlink",
      "type": "n8n-nodes-base.keyValueStore",
      "typeVersion": 1,
      "position": [
        720,
        180
      ]
    },
    {
      "parameters": {
        "functionCode": "const xml2js = require('xml2js');\nconst he = require('he'); // For HTML entity decoding\n\nconst items = $json.items || [];\nlet latestArticle = null;\nlet latestPubDate = 0;\n\n// Find the truly latest article based on pubDate\nfor (const item of items) {\n    const pubDate = new Date(item.pubDate[0]).getTime();\n    if (pubDate > latestPubDate) {\n        latestPubDate = pubDate;\n        latestArticle = item;\n    }\n}\n\nif (latestArticle) {\n    const link = latestArticle.link[0];\n    const title = latestArticle.title[0];\n    // Extract slug from the link: e.g., https://neican.huangzuomin.com/newspaper/2025-06-23-06-23-ai-/ -> 2025-06-23-06-23-ai-\n    const parts = link.split('/').filter(p => p);\n    const slug = parts[parts.length - 1]; // This should be the slug part\n    \n    // Construct GitHub raw URL\n    const githubRawUrl = `https://raw.githubusercontent.com/huangzuomin/AInews/main/content/newspaper/${slug}.md`;\n\n    return [{\n        json: {\n            rss_title: he.decode(title),\n            rss_link: link,\n            rss_pubDate: latestPubDate,\n            rss_slug: slug,\n            github_raw_url: githubRawUrl\n        }\n    }];\n} else {\n    return []; // No articles found\n}",
        "xmlInput": "={{$json.data}}",
        "xmlOutput": "items"
      },
      "name": "Parse RSS & Extract Latest",
      "type": "n8n-nodes-base.xml",
      "typeVersion": 1,
      "position": [
        500,
        350
      ]
    },
    {
      "parameters": {
        "conditions": [
          {
            "value1": "={{$json.rss_slug}}",
            "value2": "={{$node[\"Get Last Published Permlink\"].json[\"value\"]}}",
            "type": "string",
            "operator": "stringIsNotEqualTo"
          }
        ],
        "combineOperation": "and"
      },
      "name": "Is New Article?",
      "type": "n8n-nodes-base.if",
      "typeVersion": 1,
      "position": [
        940,
        180
      ]
    },
    {
      "parameters": {
        "url": "={{$json.github_raw_url}}",
        "responseFormat": "string",
        "options": {}
      },
      "name": "Get Markdown Content",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [
        1160,
        180
      ]
    },
    {
      "parameters": {
        "functionCode": "const yaml = require('js-yaml');\nconst removeMd = require('remove-markdown'); // Optional, for summary/description if needed\n\nconst markdownContent = $json.data;\nconst frontMatterRegex = /^---\\n([\\s\\S]*?)\\n---\\n([\\s\\S]*)$/;\nconst match = markdownContent.match(frontMatterRegex);\n\nlet frontMatter = {};\nlet body = markdownContent;\n\nif (match) {\n    try {\n        frontMatter = yaml.load(match[1]);\n        body = match[2];\n    } catch (e) {\n        console.error('Error parsing YAML Front Matter:', e);\n        // Fallback: Treat as no front matter or malformed\n    }\n}\n\n// Steemit requires a parent_permlink for top-level posts, usually a root tag like 'test' or 'cn'\n// For this workflow, we'll use the first tag from the article as the parent_permlink\n// If no tags, or first tag is invalid, you might want a default like 'hive' or 'cn'\nlet parentPermlink = 'cn'; // Default if no valid tags\n\n// Process tags\nlet tags = [];\nif (frontMatter.tags) {\n    if (Array.isArray(frontMatter.tags)) {\n        tags = frontMatter.tags.map(tag => String(tag).toLowerCase().replace(/[^a-z0-9-]/g, '')).filter(tag => tag);\n    } else if (typeof frontMatter.tags === 'string') {\n        tags = frontMatter.tags.split(/[,\\s]+/).map(tag => String(tag).toLowerCase().replace(/[^a-z0-9-]/g, '')).filter(tag => tag);\n    }\n    if (tags.length > 5) {\n        tags = tags.slice(0, 5); // Steemit max 5 tags\n    }\n    if (tags.length > 0) {\n        parentPermlink = tags[0]; // Use first tag as parent_permlink\n    }\n}\n\n// Generate Steemit Permlink\nlet steemitPermlink = frontMatter.slug || frontMatter.permlink; // Priority: use existing slug/permlink\nif (!steemitPermlink) {\n    // Fallback: generate from title\n    steemitPermlink = frontMatter.title\n        ? frontMatter.title.toLowerCase()\n            .replace(/[^a-z0-9\\s-]/g, '') // Remove non-alphanumeric except spaces and hyphens\n            .replace(/\\s+/g, '-')       // Replace spaces with hyphens\n            .replace(/^-+|-+$/g, '')    // Trim hyphens from start/end\n        : `post-${Date.now()}`; // Last resort fallback\n}\n\n// Ensure permlink is safe and unique enough\n// For production, consider checking uniqueness against Steemit or adding a timestamp if not unique enough by itself\n// For this workflow, we rely on the slug/generated title being mostly unique.\n\nreturn [{\n    json: {\n        title: frontMatter.title,\n        body: body.trim(), // Trim leading/trailing whitespace from body\n        tags: tags,\n        permlink: steemitPermlink,\n        parent_permlink: parentPermlink,\n        // Pass the original RSS slug for updating the last published record\n        rss_slug: $json.rss_slug\n    }\n}];",
        "additionalOptions": {
          "nodeDependencies": [
            "js-yaml",
            "remove-markdown"
          ]
        }
      },
      "name": "Parse Markdown & Prepare Data",
      "type": "n8n-nodes-base.code",
      "typeVersion": 1,
      "position": [
        1380,
        180
      ]
    },
    {
      "parameters": {
        "url": "http://your-steemit-publish-service-ip-or-domain:3000/publish-steemit",
        "method": "POST",
        "jsonBody": true,
        "options": {
          "sendOnlySet": true
        },
        "bodyParameters": {
          "parameters": [
            {
              "name": "author",
              "value": "your-steemit-username"
            },
            {
              "name": "title",
              "value": "={{$json.title}}"
            },
            {
              "name": "body",
              "value": "={{$json.body}}"
            },
            {
              "name": "permlink",
              "value": "={{$json.permlink}}"
            },
            {
              "name": "parent_permlink",
              "value": "={{$json.parent_permlink}}"
            },
            {
              "name": "tags",
              "value": "={{$json.tags}}"
            },
            {
              "name": "posting_key",
              "value": "={{$credential.SteemitPostingKey.postingKey}}"
            }
          ]
        }
      },
      "name": "Publish to Steemit",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 1,
      "position": [
        1600,
        180
      ]
    },
    {
      "parameters": {
        "operation": "setItem",
        "key": "last_published_permlink",
        "value": "={{$json.rss_slug}}"
      },
      "name": "Update Last Published Permlink",
      "type": "n8n-nodes-base.keyValueStore",
      "typeVersion": 1,
      "position": [
        1820,
        180
      ]
    },
    {
      "parameters": {
        "node": "Get RSS Feed",
        "message": "Error getting RSS feed: {{ $error.message }}",
        "trigger": "error"
      },
      "name": "Error Notification (RSS)",
      "type": "n8n-nodes-base.noOp",
      "typeVersion": 1,
      "position": [
        500,
        60
      ]
    },
    {
      "parameters": {
        "node": "Get Markdown Content",
        "message": "Error getting Markdown content: {{ $error.message }}",
        "trigger": "error"
      },
      "name": "Error Notification (Markdown)",
      "type": "n8n-nodes-base.noOp",
      "typeVersion": 1,
      "position": [
        1160,
        60
      ]
    },
    {
      "parameters": {
        "node": "Publish to Steemit",
        "message": "Error publishing to Steemit: {{ $error.message }}",
        "trigger": "error"
      },
      "name": "Error Notification (Steemit)",
      "type": "n8n-nodes-base.noOp",
      "typeVersion": 1,
      "position": [
        1600,
        60
      ]
    }
  ],
  "connections": {
    "Daily Trigger (09:00 AM)": {
      "main": [
        [
          "Get RSS Feed",
          0
        ]
      ]
    },
    "Get RSS Feed": {
      "main": [
        [
          "Parse RSS & Extract Latest",
          0
        ]
      ],
      "error": [
        [
          "Error Notification (RSS)",
          0
        ]
      ]
    },
    "Get Last Published Permlink": {
      "main": [
        [
          "Is New Article?",
          0
        ]
      ]
    },
    "Parse RSS & Extract Latest": {
      "main": [
        [
          "Get Last Published Permlink",
          0
        ]
      ]
    },
    "Is New Article?": {
      "main": [
        [
          "Get Markdown Content",
          0
        ]
      ]
    },
    "Get Markdown Content": {
      "main": [
        [
          "Parse Markdown & Prepare Data",
          0
        ]
      ],
      "error": [
        [
          "Error Notification (Markdown)",
          0
        ]
      ]
    },
    "Parse Markdown & Prepare Data": {
      "main": [
        [
          "Publish to Steemit",
          0
        ]
      ]
    },
    "Publish to Steemit": {
      "main": [
        [
          "Update Last Published Permlink",
          0
        ]
      ],
      "error": [
        [
          "Error Notification (Steemit)",
          0
        ]
      ]
    }
  }
}
```

---

### **如何导入和配置工作流：**

1.  **复制 JSON 代码：** 复制上述所有 JSON 代码。
2.  **导入 n8n：**
    *   打开您的 n8n 实例。
    *   点击左侧菜单栏的 "Workflows" (工作流)。
    *   点击右上角的 "New" (新建) 按钮，然后选择 "Import from JSON" (从 JSON 导入)。
    *   将复制的 JSON 代码粘贴到弹出的窗口中，然后点击 "Import" (导入)。
3.  **配置 Credential：**
    *   点击左侧菜单栏的 "Credentials" (凭证)。
    *   点击 "New Credential" (新建凭证)。
    *   选择 "Generic Credential"。
    *   在 "Credential Name" (凭证名称) 字段输入 `SteemitPostingKey` (必须与工作流中使用的名称一致)。
    *   在 "Keys" 部分，点击 "Add Key"。
        *   "Name" (名称) 输入 `postingKey` (必须与工作流中使用的名称一致)。
        *   "Value" (值) 输入您的 Steemit `Posting Key` (这是一个非常敏感的密钥，请务必妥善保管)。
    *   点击 "Create" (创建)。
4.  **配置 "Publish to Steemit" 节点：**
    *   在工作流中找到名为 "Publish to Steemit" 的 `HTTP Request` 节点。
    *   双击打开其设置。
    *   在 "URL" 字段中，**将 `http://your-steemit-publish-service-ip-or-domain:3000/publish-steemit` 替换为您实际部署的 Steemit 中间服务的完整 URL。**
    *   在 "Body Parameters" -> "author" 字段，**将 `your-steemit-username` 替换为您的 Steemit 用户名。**
5.  **配置 "Daily Trigger (09:00 AM)" 节点：**
    *   根据需要调整触发时间。默认设置为每天上午9点。
6.  **保存工作流：** 点击右上角的 "Save" (保存) 按钮。
7.  **激活工作流：** 切换工作流右上角的 "Active" (激活) 开关，使其变为绿色，工作流将开始按计划执行。

### **关于 "Parse RSS & Extract Latest" Code 节点中的逻辑：**

*   **RSS 解析：** 使用 `xml2js` 库解析 RSS XML。
*   **最新文章判断：** 遍历 RSS `item` 列表，根据 `pubDate` 找出最新的文章。
*   **GitHub Raw URL 构建：**
    *   从 `item.link[0]` 中提取 slug。
    *   通过 `https://raw.githubusercontent.com/huangzuomin/AInews/main/content/newspaper/${slug}.md` 模板构建出 Markdown 文件的 GitHub raw URL。**请确保 `huangzuomin/AInews` 与您的实际 GitHub 仓库匹配。**

### **关于 "Parse Markdown & Prepare Data" Code 节点中的逻辑：**

*   **YAML Front Matter 解析：** 使用 `js-yaml` 库解析 Markdown 文件开头的 YAML Front Matter。
*   **内容分离：** 将 Front Matter 和文章正文分离。
*   **标签处理：**
    *   从 `frontMatter.tags` 中获取标签。
    *   将标签转换为小写，移除非法字符，并过滤掉空标签。
    *   **限制为最多5个标签** (`tags.slice(0, 5)`)。
*   **Steemit Permlink 生成：**
    *   **优先使用 `frontMatter.slug` 或 `frontMatter.permlink`。**
    *   如果不存在，则根据 `frontMatter.title` 自动生成一个适合 URL 的 permlink (全小写，空格替换为连字符，移除特殊字符)。
    *   **重要：** 对于生产环境，建议在生成 permlink 时考虑与 Steemit 现有文章的唯一性。简单的日期或时间戳可以在生成时确保唯一性，但可能会影响 URL 的美观性。目前工作流假定由 title 生成的 permlink 结合发布频率足够唯一。
*   **`parent_permlink`：** 默认设置为 `cn`。如果文章有标签，则使用第一个标签作为 `parent_permlink`。这是 Steemit 发布主帖时的一个常见要求。
*   **Code 节点依赖：** 请确保您的 n8n 环境允许安装和运行 `js-yaml` 库。n8n 通常会自动处理 `nodeDependencies` 字段中列出的包。

### **错误处理：**

*   工作流包含了基础的错误处理节点 (`Error Notification (RSS)`, `Error Notification (Markdown)`, `Error Notification (Steemit)`)。它们当前只是 `NoOp` 节点，没有任何实际操作。
*   **推荐：** 您可以连接这些 `NoOp` 节点到 `Email` 节点、`Slack` 节点或其他通知服务，以便在工作流执行失败时收到实时通知。只需将 `NoOp` 节点替换为或连接到您选择的通知节点即可。

---
 