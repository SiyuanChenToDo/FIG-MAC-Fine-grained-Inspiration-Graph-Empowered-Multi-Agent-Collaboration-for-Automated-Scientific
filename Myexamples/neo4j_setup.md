# Neo4j 启动与连接流程

本文档记录了在当前服务器中从安装 Neo4j 到脚本成功连接 Neo4j 的完整操作步骤，并列出了向量数据库与图数据库的数据存储路径。

## 环境准备

- **操作系统**: Ubuntu 22.04.3 LTS
- **Python**: 3.12.3 (Anaconda)

## 安装 Neo4j

1. **安装 Docker (可选)**  
   ```bash
   sudo apt-get update
   sudo apt-get install -y docker.io
   ```
   > 注: 在容器环境内 Docker 守护进程无法正常启动，后续改为直接安装 Neo4j。

2. **添加 Neo4j 官方仓库并导入密钥**  
   ```bash
   wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
   echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
   sudo apt-get update
   ```

3. **安装 Neo4j 与 cypher-shell**  
   ```bash
   sudo apt-get install -y neo4j
   ```

## 配置 Neo4j

1. **修改 Bolt 端口** (`/etc/neo4j/neo4j.conf`)  
   ```ini
   server.bolt.listen_address=:17687
   server.bolt.advertised_address=:17687
   ```

2. **启用 APOC 插件**  
   - 下载插件:
     ```bash
     sudo wget https://github.com/neo4j/apoc/releases/download/5.26.0/apoc-5.26.0-core.jar \
       -O /var/lib/neo4j/plugins/apoc-5.26.0-core.jar
     ```
   - 在 `neo4j.conf` 中允许 APOC:
     ```ini
     dbms.security.procedures.unrestricted=apoc.*
     dbms.security.procedures.allowlist=apoc.*
     ```

3. **设置初始密码**  
   ```bash
   sudo neo4j-admin dbms set-initial-password ai4sci123456
   ```

4. **迁移历史数据 (使用原 Docker 数据目录)**
   ```bash
   sudo systemctl stop neo4j    # 若运行在 systemd 环境，或使用 neo4j stop
   sudo mv /var/lib/neo4j/data /var/lib/neo4j/data.backup
   sudo ln -s /root/autodl-tmp/data/graph_data/data /var/lib/neo4j/data
   sudo chown -R neo4j:neo4j /root/autodl-tmp/data/graph_data/data
   ```

## 启动与验证

1. **启动 Neo4j**  
   ```bash
   sudo neo4j start
   ```

2. **验证服务状态**
   - 查看进程: `ps aux | grep neo4j`
   - 查看端口: `ss -tuln | grep 17687` 或 `netstat -tuln`

3. **命令行验证连接**  
   ```bash
   cypher-shell -a bolt://localhost:17687 -u neo4j -p ai4sci123456 "MATCH (n) RETURN count(n) AS total;"
   ```
   预期返回节点总数，例如 `182899`。

4. **Python 脚本验证** (`Neo4jGraph`)
   ```python
   from camel.storages import Neo4jGraph

   n4j = Neo4jGraph(
       url="bolt://localhost:17687",
       username="neo4j",
       password="ai4sci123456"
   )
   print(n4j.query("RETURN 'Connection successful!' AS status"))
   ```

## 向量与图数据的存储路径

- **向量数据库 (FAISS) 存储路径**:  
  `/root/autodl-tmp/Myexamples/vdb/camel_faiss_storage`

- **图数据库 (Neo4j) 数据目录**:  
  `/root/autodl-tmp/data/graph_data/data`

  该目录通过符号链接挂载为 Neo4j 的数据目录 `/var/lib/neo4j/data`。

## 注意事项

- 当前 APOC 插件版本 `5.26.0` 与 Neo4j `2025.09.0` 存在版本提示警告，但在实际使用中仍可加载主要功能。如需消除警告，可将 APOC 升级到 `5.25.x` 或将 Neo4j 降级到 `5.26.x`。
- 如需重置数据库，可删除或替换 `/root/autodl-tmp/data/graph_data/data` 目录中的内容，随后重新启动 Neo4j。
