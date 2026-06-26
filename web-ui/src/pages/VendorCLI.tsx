import { useRef, useEffect } from 'react'

import VendorTerminal from '../components/VendorTerminal'
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/Card'
import { Badge } from '../components/ui/Badge'

const VendorCLI = () => {
  const headerRef = useRef<HTMLDivElement>(null)
  const commandsRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (headerRef.current) {
    }
    if (commandsRef.current) {
    }
  }, [])

  return (
    <div className="space-y-6">
      <div ref={headerRef}>
        <h1 className="text-2xl font-bold">多厂商 CLI 终端</h1>
        <p className="text-muted-foreground mt-1">
          支持 Cisco IOS 和华为 VRP 命令语法
        </p>
      </div>

      <VendorTerminal />

      <Card ref={commandsRef}>
        <CardHeader>
          <CardTitle>支持的命令</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <h4 className="text-muted-foreground mb-2 font-medium">Cisco IOS</h4>
              <ul className="space-y-2">
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">show ip interface brief</Badge>
                  <span className="text-muted-foreground">显示接口</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">show ip route</Badge>
                  <span className="text-muted-foreground">路由表</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">show running-config</Badge>
                  <span className="text-muted-foreground">运行配置</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">ping</Badge>
                  <span className="text-muted-foreground">测试连通性</span>
                </li>
              </ul>
            </div>
            <div>
              <h4 className="text-muted-foreground mb-2 font-medium">华为 VRP</h4>
              <ul className="space-y-2">
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">display ip interface brief</Badge>
                  <span className="text-muted-foreground">显示接口</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">display ip routing-table</Badge>
                  <span className="text-muted-foreground">路由表</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">display current-configuration</Badge>
                  <span className="text-muted-foreground">运行配置</span>
                </li>
                <li className="flex items-center gap-2">
                  <Badge variant="outline" className="font-mono text-xs">ping</Badge>
                  <span className="text-muted-foreground">测试连通性</span>
                </li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}

export default VendorCLI
