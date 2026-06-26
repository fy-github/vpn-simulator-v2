import React, { useState, useRef, useEffect } from 'react';

interface CommandHistoryEntry {
  command: string;
  output: string;
  success: boolean;
  timestamp: string;
}

interface VendorCommand {
  command: string;
  description: string;
  mode: string;
  aliases: string[];
}

const VendorTerminal: React.FC = () => {
  const [vendor, setVendor] = useState<'cisco' | 'huawei'>('cisco');
  const [input, setInput] = useState('');
  const [history, setHistory] = useState<CommandHistoryEntry[]>([]);
  const [commands, setCommands] = useState<VendorCommand[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const terminalRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // 加载支持的命令
  useEffect(() => {
    fetchCommands();
  }, [vendor]);

  // 自动滚动到底部
  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [history]);

  const fetchCommands = async () => {
    try {
      const response = await fetch(`/api/v1/vendor-cli/commands?vendor=${vendor}`);
      const data = await response.json();
      setCommands(data.commands || []);
    } catch (error) {
      console.error('Failed to fetch commands:', error);
    }
  };

  const executeCommand = async () => {
    if (!input.trim()) return;

    const command = input.trim();
    setInput('');
    setIsLoading(true);

    try {
      const response = await fetch('/api/v1/vendor-cli/execute', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ vendor, command })
      });

      const result = await response.json();
      setHistory(prev => [...prev, {
        command: result.command,
        output: result.output,
        success: result.success,
        timestamp: result.timestamp
      }]);
    } catch (error) {
      setHistory(prev => [...prev, {
        command,
        output: 'Error: Failed to execute command',
        success: false,
        timestamp: new Date().toISOString()
      }]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      executeCommand();
    }
  };

  const clearHistory = () => {
    setHistory([]);
  };

  const getPrompt = () => {
    if (vendor === 'cisco') {
      return 'Router>';
    }
    return '<Router>';
  };

  return (
    <div className="bg-gray-900 rounded-lg overflow-hidden">
      {/* 控制栏 */}
      <div className="bg-gray-800 px-4 py-2 flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <select
            value={vendor}
            onChange={(e) => setVendor(e.target.value as 'cisco' | 'huawei')}
            className="bg-gray-700 text-white px-3 py-1 rounded text-sm"
          >
            <option value="cisco">Cisco IOS</option>
            <option value="huawei">华为 VRP</option>
          </select>
          <span className="text-gray-400 text-sm">
            {commands.length} 命令可用
          </span>
        </div>
        <button
          onClick={clearHistory}
          className="text-gray-400 hover:text-white text-sm"
        >
          清除
        </button>
      </div>

      {/* 终端输出 */}
      <div
        ref={terminalRef}
        className="p-4 h-96 overflow-y-auto font-mono text-sm"
        onClick={() => inputRef.current?.focus()}
      >
        {/* 欢迎信息 */}
        <div className="text-green-400 mb-4">
          <div>VPN Simulator - {vendor === 'cisco' ? 'Cisco IOS' : '华为 VRP'} 模拟终端</div>
          <div className="text-gray-500">输入命令执行，支持 Tab 自动补全</div>
          <div className="text-gray-500">---</div>
        </div>

        {/* 命令历史 */}
        {history.map((entry, index) => (
          <div key={index} className="mb-2">
            <div className="text-yellow-400">
              {getPrompt()} {entry.command}
            </div>
            <pre className={`whitespace-pre-wrap ${entry.success ? 'text-gray-300' : 'text-red-400'}`}>
              {entry.output}
            </pre>
          </div>
        ))}

        {/* 输入提示 */}
        <div className="flex items-center text-yellow-400">
          <span>{getPrompt()} </span>
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1 bg-transparent outline-none ml-1"
            placeholder={isLoading ? '执行中...' : '输入命令...'}
            disabled={isLoading}
            autoFocus
          />
        </div>
      </div>

      {/* 命令提示 */}
      <div className="bg-gray-800 px-4 py-2 border-t border-gray-700">
        <div className="text-gray-500 text-xs">
          常用命令: {commands.slice(0, 5).map(c => c.command).join(' | ')}
        </div>
      </div>
    </div>
  );
};

export default VendorTerminal;
