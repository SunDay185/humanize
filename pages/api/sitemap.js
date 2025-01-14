import fs from 'fs';
import path from 'path';

export default function handler(req, res) {
  // 设置正确的 Content-Type
  res.setHeader('Content-Type', 'application/xml');
  
  // 读取 sitemap 文件
  const sitemap = fs.readFileSync(path.join(process.cwd(), 'public', 'sitemap.xml'), 'utf-8');
  
  // 发送响应
  res.status(200).send(sitemap);
} 