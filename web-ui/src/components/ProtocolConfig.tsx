import { useState } from 'react'
import { Input } from './ui/Input'
import { Select } from './ui/Select'
import { Button } from './ui/Button'
import { Tabs } from './ui/Tabs'

interface User {
  username: string
  password: string
}

interface ProtocolConfigProps {
  protocol: string
  config: Record<string, unknown>
  onSave: (config: Record<string, unknown>) => void
  onCancel: () => void
}

const UserTable = ({ users, onChange }: { users: User[]; onChange: (users: User[]) => void }) => {
  const addUser = () => {
    onChange([...users, { username: '', password: '' }])
  }

  const removeUser = (index: number) => {
    onChange(users.filter((_, i) => i !== index))
  }

  const updateUser = (index: number, field: keyof User, value: string) => {
    const updated = [...users]
    updated[index] = { ...updated[index], [field]: value }
    onChange(updated)
  }

  return (
    <div className="space-y-2">
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b">
              <th className="text-left py-2 px-2 text-muted-foreground">用户名</th>
              <th className="text-left py-2 px-2 text-muted-foreground">密码</th>
              <th className="text-right py-2 px-2 text-muted-foreground">操作</th>
            </tr>
          </thead>
          <tbody>
            {users.map((user, index) => (
              <tr key={index} className="border-b">
                <td className="py-2 px-2">
                  <input
                    type="text"
                    value={user.username}
                    onChange={(e) => updateUser(index, 'username', e.target.value)}
                    className="w-full px-2 py-1 bg-muted rounded text-sm"
                    placeholder="用户名"
                  />
                </td>
                <td className="py-2 px-2">
                  <input
                    type="password"
                    value={user.password}
                    onChange={(e) => updateUser(index, 'password', e.target.value)}
                    className="w-full px-2 py-1 bg-muted rounded text-sm"
                    placeholder="密码"
                  />
                </td>
                <td className="py-2 px-2 text-right">
                  <Button variant="ghost" size="sm" onClick={() => removeUser(index)}>
                    删除
                  </Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Button variant="outline" size="sm" onClick={addUser}>
        + 添加用户
      </Button>
    </div>
  )
}

const PPTPConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const users = (config.auth_users as User[]) || []
  return {
    tabs: [
      {
        id: 'users',
        label: '用户管理',
        content: (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">双击单元格可编辑用户名/密码</p>
            <UserTable users={users} onChange={(u) => onChange('auth_users', u)} />
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Input label="MRU (最大接收单元)" type="number" value={String(config.mru || 1400)} onChange={(e) => onChange('mru', parseInt(e.target.value))} />
            <Input label="MTU (最大传输单元)" type="number" value={String(config.mtu || 1400)} onChange={(e) => onChange('mtu', parseInt(e.target.value))} />
            <Input label="客户端IP 起始" value={String(config.client_ip_pool_start || '192.168.100.10')} onChange={(e) => onChange('client_ip_pool_start', e.target.value)} />
            <Input label="客户端IP 结束" value={String(config.client_ip_pool_end || '192.168.100.50')} onChange={(e) => onChange('client_ip_pool_end', e.target.value)} />
            <Input label="服务端隧道IP" value={String(config.server_tun_ip || '192.168.100.1')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
            <Input label="主 DNS" value={String(config.dns1 || '8.8.8.8')} onChange={(e) => onChange('dns1', e.target.value)} />
            <Input label="辅 DNS" value={String(config.dns2 || '8.8.4.4')} onChange={(e) => onChange('dns2', e.target.value)} />
            <Select
              label="认证方式"
              options={[{ value: 'mschapv2', label: 'MS-CHAPv2' }, { value: 'pap', label: 'PAP' }]}
              value={String(config.auth_method || 'mschapv2')}
              onChange={(v) => onChange('auth_method', v)}
            />
          </div>
        ),
      },
    ],
  }
}

const L2TPConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const users = (config.auth_users as User[]) || []
  return {
    tabs: [
      {
        id: 'users',
        label: '用户管理',
        content: (
          <div className="space-y-4">
            <UserTable users={users} onChange={(u) => onChange('auth_users', u)} />
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Input label="MRU" type="number" value={String(config.mru || 1400)} onChange={(e) => onChange('mru', parseInt(e.target.value))} />
            <Input label="MTU" type="number" value={String(config.mtu || 1400)} onChange={(e) => onChange('mtu', parseInt(e.target.value))} />
            <Input label="预共享密钥 (PSK)" value={String(config.psk || '')} onChange={(e) => onChange('psk', e.target.value)} placeholder="L2TP/IPSec 预共享密钥" />
            <Input label="本地标识" value={String(config.local_id || '')} onChange={(e) => onChange('local_id', e.target.value)} placeholder="IP或域名，留空=自动" />
            <Input label="对方标识" value={String(config.peer_id || '')} onChange={(e) => onChange('peer_id', e.target.value)} placeholder="IP或域名，留空=任意" />
            <Input label="客户端IP 起始" value={String(config.client_ip_pool_start || '192.168.101.10')} onChange={(e) => onChange('client_ip_pool_start', e.target.value)} />
            <Input label="客户端IP 结束" value={String(config.client_ip_pool_end || '192.168.101.50')} onChange={(e) => onChange('client_ip_pool_end', e.target.value)} />
            <Input label="服务端隧道IP" value={String(config.server_tun_ip || '192.168.101.1')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
            <div className="flex items-center space-x-2">
              <input type="checkbox" id="use_ipsec" checked={config.use_ipsec !== false} onChange={(e) => onChange('use_ipsec', e.target.checked)} className="h-4 w-4" />
              <label htmlFor="use_ipsec" className="text-sm">启用 IPSec 保护 (L2TP/IPSec)</label>
            </div>
          </div>
        ),
      },
    ],
  }
}

const OpenVPNConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const users = (config.auth_users as User[]) || []
  return {
    tabs: [
      {
        id: 'auth',
        label: '认证',
        content: (
          <div className="space-y-4">
            <Select
              label="认证方式"
              options={[
                { value: 'password', label: '账号密码认证' },
                { value: 'tls-auth', label: '静态密钥 (tls-auth)' },
                { value: 'tls-crypt', label: '静态密钥 (tls-crypt)' },
              ]}
              value={String(config.auth_method_type || 'password')}
              onChange={(v) => onChange('auth_method_type', v)}
            />
            {(config.auth_method_type || 'password') === 'password' && (
              <div>
                <p className="text-sm text-muted-foreground mb-2">用户账号管理</p>
                <UserTable users={users} onChange={(u) => onChange('auth_users', u)} />
              </div>
            )}
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Select label="隧道类型" options={[{ value: 'tun', label: 'TUN' }, { value: 'tap', label: 'TAP' }]} value={String(config.tunnel_type || 'tun')} onChange={(v) => onChange('tunnel_type', v)} />
            <Select label="传输协议" options={[{ value: 'udp', label: 'UDP' }, { value: 'tcp', label: 'TCP' }]} value={String(config.transport || 'udp')} onChange={(v) => onChange('transport', v)} />
            <Select label="加密算法" options={[{ value: 'AES-256-GCM', label: 'AES-256-GCM' }, { value: 'AES-128-GCM', label: 'AES-128-GCM' }, { value: 'AES-256-CBC', label: 'AES-256-CBC' }, { value: 'CHACHA20-POLY1305', label: 'CHACHA20-POLY1305' }]} value={String(config.cipher || 'AES-256-GCM')} onChange={(v) => onChange('cipher', v)} />
            <div className="flex items-center space-x-2">
              <input type="checkbox" id="lzo" checked={config.lzo === true} onChange={(e) => onChange('lzo', e.target.checked)} className="h-4 w-4" />
              <label htmlFor="lzo" className="text-sm">启用 LZO 压缩</label>
            </div>
            <Input label="MTU" type="number" value={String(config.mtu || 1500)} onChange={(e) => onChange('mtu', parseInt(e.target.value))} />
            <Input label="客户端IP 段" value={String(config.client_ip_pool || '10.8.0.0/24')} onChange={(e) => onChange('client_ip_pool', e.target.value)} />
            <Input label="服务端隧道IP" value={String(config.server_tun_ip || '10.8.0.1')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
          </div>
        ),
      },
      {
        id: 'certs',
        label: '证书/密钥',
        content: (
          <div className="space-y-4">
            <Input label="CA 证书" value={String(config.ca_cert || '')} onChange={(e) => onChange('ca_cert', e.target.value)} placeholder="CA 证书路径 (.pem/.crt)" />
            <Input label="客户端证书" value={String(config.client_cert || '')} onChange={(e) => onChange('client_cert', e.target.value)} placeholder="客户端证书路径" />
            <Input label="客户端私钥" value={String(config.client_key || '')} onChange={(e) => onChange('client_key', e.target.value)} placeholder="客户端私钥路径" />
          </div>
        ),
      },
      {
        id: 'routes',
        label: '路由 & 附加',
        content: (
          <div className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground mb-2 block">服务器路由推送 (每行一条)</label>
              <textarea
                value={String(config.push_routes || '')}
                onChange={(e) => onChange('push_routes', e.target.value)}
                className="w-full px-3 py-2 bg-muted rounded text-sm"
                rows={3}
                placeholder="10.0.0.0 255.255.255.0"
              />
            </div>
            <div>
              <label className="text-sm text-muted-foreground mb-2 block">附加配置 (OpenVPN 原生指令，每行一条)</label>
              <textarea
                value={String(config.extra_config || '')}
                onChange={(e) => onChange('extra_config', e.target.value)}
                className="w-full px-3 py-2 bg-muted rounded text-sm"
                rows={3}
              />
            </div>
          </div>
        ),
      },
    ],
  }
}

const IPSecConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const phase1 = (config.phase1 as Record<string, unknown>) || {}
  const phase2 = (config.phase2 as Record<string, unknown>) || {}
  return {
    tabs: [
      {
        id: 'auth',
        label: '认证',
        content: (
          <div className="space-y-4">
            <Select
              label="认证方式"
              options={[{ value: 'psk', label: '预共享密钥 (PSK)' }, { value: 'cert', label: '自签证书' }]}
              value={String(config.auth_type || 'psk')}
              onChange={(v) => onChange('auth_type', v)}
            />
            {(config.auth_type || 'psk') === 'psk' ? (
              <Input label="PSK" value={String(config.psk || '')} onChange={(e) => onChange('psk', e.target.value)} placeholder="PSK 字符串" />
            ) : (
              <div className="space-y-4">
                <Input label="CA 证书" value={String(config.ca_cert || '')} onChange={(e) => onChange('ca_cert', e.target.value)} />
                <Input label="服务端证书" value={String(config.server_cert || '')} onChange={(e) => onChange('server_cert', e.target.value)} />
                <Input label="服务端私钥" value={String(config.server_key || '')} onChange={(e) => onChange('server_key', e.target.value)} />
              </div>
            )}
          </div>
        ),
      },
      {
        id: 'phase',
        label: 'Phase 参数',
        content: (
          <div className="space-y-4">
            <p className="text-sm font-medium">Phase 1</p>
            <Select label="加密" options={[{ value: 'aes256', label: 'AES-256' }, { value: 'aes128', label: 'AES-128' }, { value: '3des', label: '3DES' }]} value={String(phase1.encryption || 'aes256')} onChange={(v) => onChange('phase1', { ...phase1, encryption: v })} />
            <Select label="哈希" options={[{ value: 'sha256', label: 'SHA-256' }, { value: 'sha1', label: 'SHA-1' }, { value: 'md5', label: 'MD5' }]} value={String(phase1.hash || 'sha256')} onChange={(v) => onChange('phase1', { ...phase1, hash: v })} />
            <Input label="DH 组" type="number" value={String(phase1.dh_group || 14)} onChange={(e) => onChange('phase1', { ...phase1, dh_group: parseInt(e.target.value) })} />
            <p className="text-sm font-medium mt-4">Phase 2</p>
            <Select label="加密" options={[{ value: 'aes256', label: 'AES-256' }, { value: 'aes128', label: 'AES-128' }, { value: '3des', label: '3DES' }]} value={String(phase2.encryption || 'aes256')} onChange={(v) => onChange('phase2', { ...phase2, encryption: v })} />
            <Select label="认证" options={[{ value: 'sha256', label: 'SHA-256' }, { value: 'sha1', label: 'SHA-1' }, { value: 'md5', label: 'MD5' }]} value={String(phase2.auth || 'sha256')} onChange={(v) => onChange('phase2', { ...phase2, auth: v })} />
            <Input label="DH 组" type="number" value={String(phase2.dh_group || 14)} onChange={(e) => onChange('phase2', { ...phase2, dh_group: parseInt(e.target.value) })} />
            <div className="flex items-center space-x-2">
              <input type="checkbox" id="nat_t" checked={config.nat_t !== false} onChange={(e) => onChange('nat_t', e.target.checked)} className="h-4 w-4" />
              <label htmlFor="nat_t" className="text-sm">启用 NAT-T 穿越 (UDP 4500)</label>
            </div>
          </div>
        ),
      },
    ],
  }
}

const IKEv2Config = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  return {
    tabs: [
      {
        id: 'auth',
        label: '认证',
        content: (
          <div className="space-y-4">
            <Select
              label="认证方式"
              options={[{ value: 'psk', label: '预共享密钥 (PSK)' }, { value: 'cert', label: '自签证书' }, { value: 'eap-mschapv2', label: 'EAP-MSCHAPv2' }]}
              value={String(config.auth_method || 'psk')}
              onChange={(v) => onChange('auth_method', v)}
            />
            {(config.auth_method || 'psk') === 'psk' && (
              <Input label="PSK" value={String(config.psk || '')} onChange={(e) => onChange('psk', e.target.value)} />
            )}
            {(config.auth_method || 'psk') === 'cert' && (
              <div className="space-y-4">
                <Input label="CA 证书" value={String(config.ca_cert || '')} onChange={(e) => onChange('ca_cert', e.target.value)} />
                <Input label="服务端证书" value={String(config.server_cert || '')} onChange={(e) => onChange('server_cert', e.target.value)} />
                <Input label="服务端私钥" value={String(config.server_key || '')} onChange={(e) => onChange('server_key', e.target.value)} />
              </div>
            )}
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Input label="客户端IP 段" value={String(config.client_ip_pool || '10.10.0.0/24')} onChange={(e) => onChange('client_ip_pool', e.target.value)} />
            <Select label="加密算法" options={[{ value: 'AES_CBC_256', label: 'AES-CBC-256' }, { value: 'AES_GCM_256', label: 'AES-GCM-256' }, { value: 'AES_CBC_128', label: 'AES-CBC-128' }]} value={String(config.p1_encrypt || 'AES_CBC_256')} onChange={(v) => onChange('p1_encrypt', v)} />
            <Select label="DH 组" options={[{ value: 'MODP_2048', label: 'MODP-2048' }, { value: 'ECP_256', label: 'ECP-256' }, { value: 'MODP_3072', label: 'MODP-3072' }]} value={String(config.p1_dh || 'MODP_2048')} onChange={(v) => onChange('p1_dh', v)} />
          </div>
        ),
      },
    ],
  }
}

const WireGuardConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  return {
    tabs: [
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Input label="服务端隧道IP/掩码" value={String(config.server_tun_ip || '10.20.0.1/24')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
            <Input label="私钥 (Base64)" value={String(config.server_private_key || '')} onChange={(e) => onChange('server_private_key', e.target.value)} placeholder="留空=自动生成" />
            <Input label="公钥 (只读)" value={String(config.server_public_key || '')} onChange={() => {}} disabled />
          </div>
        ),
      },
    ],
  }
}

const SSTPConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const users = (config.auth_users as Array<{ username: string; password: string }>) || []
  return {
    tabs: [
      {
        id: 'users',
        label: '用户管理',
        content: (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">双击单元格可编辑用户名/密码</p>
            <UserTable users={users} onChange={(u) => onChange('auth_users', u)} />
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Input label="MTU" type="number" value={String(config.mtu || 1400)} onChange={(e) => onChange('mtu', parseInt(e.target.value))} />
            <Input label="客户端IP 起始" value={String(config.client_ip_pool_start || '192.168.102.10')} onChange={(e) => onChange('client_ip_pool_start', e.target.value)} />
            <Input label="客户端IP 结束" value={String(config.client_ip_pool_end || '192.168.102.50')} onChange={(e) => onChange('client_ip_pool_end', e.target.value)} />
            <Input label="服务端隧道IP" value={String(config.server_tun_ip || '192.168.102.1')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
            <Input label="主 DNS" value={String(config.dns1 || '8.8.8.8')} onChange={(e) => onChange('dns1', e.target.value)} />
            <Input label="辅 DNS" value={String(config.dns2 || '8.8.4.4')} onChange={(e) => onChange('dns2', e.target.value)} />
          </div>
        ),
      },
      {
        id: 'certs',
        label: '证书/密钥',
        content: (
          <div className="space-y-4">
            <Input label="CA 证书" value={String(config.ca_cert || '')} onChange={(e) => onChange('ca_cert', e.target.value)} placeholder="CA 证书路径 (.pem/.crt)" />
            <Input label="服务端证书" value={String(config.server_cert || '')} onChange={(e) => onChange('server_cert', e.target.value)} placeholder="服务端证书路径" />
            <Input label="服务端私钥" value={String(config.server_key || '')} onChange={(e) => onChange('server_key', e.target.value)} placeholder="服务端私钥路径" />
          </div>
        ),
      },
    ],
  }
}

const OpenConnectConfig = ({ config, onChange }: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => {
  const users = (config.auth_users as Array<{ username: string; password: string }>) || []
  return {
    tabs: [
      {
        id: 'users',
        label: '用户管理',
        content: (
          <div className="space-y-4">
            <p className="text-sm text-muted-foreground">双击单元格可编辑用户名/密码</p>
            <UserTable users={users} onChange={(u) => onChange('auth_users', u)} />
          </div>
        ),
      },
      {
        id: 'params',
        label: '连接参数',
        content: (
          <div className="space-y-4">
            <Select
              label="隧道类型"
              options={[{ value: 'tun', label: 'TUN' }, { value: 'tap', label: 'TAP' }]}
              value={String(config.tunnel_type || 'tun')}
              onChange={(v) => onChange('tunnel_type', v)}
            />
            <Input label="MTU" type="number" value={String(config.mtu || 1400)} onChange={(e) => onChange('mtu', parseInt(e.target.value))} />
            <Input label="客户端IP 段" value={String(config.client_ip_pool || '192.168.103.0/24')} onChange={(e) => onChange('client_ip_pool', e.target.value)} />
            <Input label="服务端隧道IP" value={String(config.server_tun_ip || '192.168.103.1')} onChange={(e) => onChange('server_tun_ip', e.target.value)} />
            <Input label="主 DNS" value={String(config.dns1 || '8.8.8.8')} onChange={(e) => onChange('dns1', e.target.value)} />
            <Input label="辅 DNS" value={String(config.dns2 || '8.8.4.4')} onChange={(e) => onChange('dns2', e.target.value)} />
          </div>
        ),
      },
      {
        id: 'certs',
        label: '证书/密钥',
        content: (
          <div className="space-y-4">
            <Input label="CA 证书" value={String(config.ca_cert || '')} onChange={(e) => onChange('ca_cert', e.target.value)} placeholder="CA 证书路径 (.pem/.crt)" />
            <Input label="服务端证书" value={String(config.server_cert || '')} onChange={(e) => onChange('server_cert', e.target.value)} placeholder="服务端证书路径" />
            <Input label="服务端私钥" value={String(config.server_key || '')} onChange={(e) => onChange('server_key', e.target.value)} placeholder="服务端私钥路径" />
          </div>
        ),
      },
    ],
  }
}

const configComponents: Record<string, (props: { config: Record<string, unknown>; onChange: (key: string, value: unknown) => void }) => { tabs: Array<{ id: string; label: string; content: React.ReactNode }> }> = {
  pptp: PPTPConfig,
  l2tp: L2TPConfig,
  openvpn: OpenVPNConfig,
  ipsec: IPSecConfig,
  ikev2: IKEv2Config,
  wireguard: WireGuardConfig,
  sstp: SSTPConfig,
  openconnect: OpenConnectConfig,
}

export default function ProtocolConfig({ protocol, config: initialConfig, onSave, onCancel }: ProtocolConfigProps) {
  const [config, setConfig] = useState<Record<string, unknown>>(initialConfig)

  const handleChange = (key: string, value: unknown) => {
    setConfig(prev => ({ ...prev, [key]: value }))
  }

  const ConfigComponent = configComponents[protocol]

  if (!ConfigComponent) {
    return (
      <div className="space-y-4">
        <p className="text-muted-foreground">此协议暂无专用配置界面</p>
        <div className="flex justify-end space-x-2">
          <Button variant="outline" onClick={onCancel}>取消</Button>
          <Button onClick={() => onSave(config)}>保存</Button>
        </div>
      </div>
    )
  }

  const { tabs } = ConfigComponent({ config, onChange: handleChange })

  return (
    <div className="space-y-4">
      <Tabs tabs={tabs} defaultTab={tabs[0]?.id} />
      <div className="flex justify-end space-x-2 pt-4 border-t">
        <Button variant="outline" onClick={onCancel}>取消</Button>
        <Button onClick={() => onSave(config)}>保存</Button>
      </div>
    </div>
  )
}
