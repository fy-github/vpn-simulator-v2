import { useTranslation } from 'react-i18next'
import { ZapIcon, InfoIcon, FileIcon } from './Icons'

interface TutorialStepInfo {
  title: string
  description: string
  packet_info: string
  rfc_reference: string
  expected_state: string
  hint: string
}

interface TutorialStepProps {
  step: TutorialStepInfo
  stepNumber: number
  totalSteps: number
  isActive: boolean
}

const TutorialStep = ({ step, stepNumber, totalSteps, isActive }: TutorialStepProps) => {
  const { t } = useTranslation()

  return (
    <div
      className={`rounded-lg border p-6 transition-all ${
        isActive
          ? 'border-primary shadow-md'
          : 'border-border opacity-70'
      }`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center space-x-3">
          <div
            className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${
              isActive
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            {stepNumber + 1}
          </div>
          <h3 className="text-lg font-semibold">{step.title}</h3>
        </div>
        <span className="text-xs text-muted-foreground">
          {stepNumber + 1} / {totalSteps}
        </span>
      </div>

      <p className="text-muted-foreground mb-4 leading-relaxed">{step.description}</p>

      {step.packet_info && (
        <div className="mb-4 p-4 bg-muted rounded-lg border border-border">
          <h4 className="text-sm font-medium text-primary mb-2">
            {t('tutorial.packetInfo', '报文信息')}
          </h4>
          <p className="text-sm text-muted-foreground font-mono whitespace-pre-wrap">
            {step.packet_info}
          </p>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        {step.rfc_reference && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-primary/10 text-primary">
            <FileIcon className="w-3 h-3 mr-1" />
            {step.rfc_reference}
          </span>
        )}

        {step.expected_state && (
          <span className="inline-flex items-center px-3 py-1 rounded-full text-xs bg-success/10 text-success">
            <ZapIcon className="w-3 h-3 mr-1" />
            {t('tutorial.expectedState', '期望状态')}: {step.expected_state}
          </span>
        )}
      </div>

      {step.hint && isActive && (
        <div className="mt-4 p-3 bg-warning/10 border border-warning/20 rounded-lg">
          <p className="text-sm text-warning">
            <InfoIcon className="w-4 h-4 inline mr-1" />
            {t('tutorial.hint', '提示')}: {step.hint}
          </p>
        </div>
      )}
    </div>
  )
}

export default TutorialStep
