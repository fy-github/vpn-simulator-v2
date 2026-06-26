import { useTranslation } from 'react-i18next'
import { FileIcon } from './Icons'

interface RFCDocument {
  number: string
  title: string
  url: string
  description: string
  published?: string
  status?: string
}

interface Reference {
  title: string
  url: string
  description: string
}

interface RFCReferenceProps {
  protocol: string
  protocolName: string
  fullName?: string
  rfcs: RFCDocument[]
  references?: Reference[]
  compact?: boolean
}

const RFCReference = ({
  protocol,
  protocolName,
  fullName,
  rfcs,
  references = [],
  compact = false,
}: RFCReferenceProps) => {
  const { t } = useTranslation()

  const hasRFC = rfcs.length > 0
  const hasReferences = references.length > 0

  if (!hasRFC && !hasReferences) {
    return (
      <div className="card p-4">
        <div className="flex items-center space-x-2 mb-2">
          <FileIcon className="w-5 h-5 text-gray-400" />
          <h3 className="font-semibold text-white">{protocolName}</h3>
        </div>
        <p className="text-dark-400 text-sm">
          {t('learning.rfc.noFormalRFC', '无正式 RFC 文档')}
        </p>
      </div>
    )
  }

  if (compact) {
    return (
      <div className="flex flex-wrap gap-2">
        {rfcs.map((rfc, index) => (
          <a
            key={index}
            href={rfc.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1 px-3 py-1.5 bg-primary-500/10 border border-primary-500/30 rounded-lg hover:bg-primary-500/20 transition-colors"
          >
            <span className="text-primary-400 font-mono text-sm">{rfc.number}</span>
            <svg
              className="w-3 h-3 text-dark-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        ))}
        {references.map((ref, index) => (
          <a
            key={`ref-${index}`}
            href={ref.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center space-x-1 px-3 py-1.5 bg-dark-700 border border-dark-600 rounded-lg hover:bg-dark-600 transition-colors"
          >
            <span className="text-dark-300 text-sm">{ref.title}</span>
            <svg
              className="w-3 h-3 text-dark-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
              />
            </svg>
          </a>
        ))}
      </div>
    )
  }

  return (
    <div className="card p-6">
      <div className="flex items-start justify-between mb-4">
        <div>
          <div className="flex items-center space-x-2">
            <FileIcon className="w-5 h-5 text-gray-400" />
            <h3 className="text-lg font-semibold text-white">{protocolName}</h3>
          </div>
          {fullName && (
            <p className="text-dark-400 text-sm mt-1 ml-7">{fullName}</p>
          )}
        </div>
        <span className="px-2 py-1 bg-dark-700 rounded text-xs text-dark-400 font-mono">
          {protocol.toUpperCase()}
        </span>
      </div>

      {/* RFC Documents */}
      {hasRFC && (
        <div className="space-y-3 mb-4">
          <h4 className="text-sm font-medium text-dark-300">
            {t('learning.rfc.documents', 'RFC 文档')}
          </h4>
          {rfcs.map((rfc, index) => (
            <a
              key={index}
              href={rfc.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-dark-700/50 rounded-lg hover:bg-dark-700 transition-colors group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="text-primary-400 font-mono font-medium">
                      {rfc.number}
                    </span>
                    {rfc.status && (
                      <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 rounded text-xs">
                        {rfc.status}
                      </span>
                    )}
                  </div>
                  <p className="text-white text-sm mt-1">{rfc.title}</p>
                  <p className="text-dark-400 text-xs mt-1">{rfc.description}</p>
                </div>
                <svg
                  className="w-4 h-4 text-dark-500 group-hover:text-primary-400 transition-colors ml-2 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </div>
              {rfc.published && (
                <p className="text-dark-500 text-xs mt-2">
                  {t('learning.rfc.published', '发布于')}: {rfc.published}
                </p>
              )}
            </a>
          ))}
        </div>
      )}

      {/* Other References */}
      {hasReferences && (
        <div className="space-y-3">
          <h4 className="text-sm font-medium text-dark-300">
            {t('learning.rfc.otherReferences', '其他参考资料')}
          </h4>
          {references.map((ref, index) => (
            <a
              key={index}
              href={ref.url}
              target="_blank"
              rel="noopener noreferrer"
              className="block p-3 bg-dark-700/50 rounded-lg hover:bg-dark-700 transition-colors group"
            >
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <p className="text-white text-sm">{ref.title}</p>
                  <p className="text-dark-400 text-xs mt-1">{ref.description}</p>
                </div>
                <svg
                  className="w-4 h-4 text-dark-500 group-hover:text-primary-400 transition-colors ml-2 flex-shrink-0"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"
                  />
                </svg>
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}

export default RFCReference
