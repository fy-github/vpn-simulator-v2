import { useEffect, useRef } from 'react'
import gsap from 'gsap'

interface UseGSAPOptions {
  dependencies?: unknown[]
  scope?: React.RefObject<HTMLElement>
}

export function useGSAP(
  callback: (context: gsap.Context) => void,
  options: UseGSAPOptions = {}
) {
  const { dependencies = [], scope } = options
  const contextRef = useRef<gsap.Context | null>(null)

  useEffect(() => {
    const context = gsap.context(() => {
      callback(context)
    }, scope?.current || undefined)

    contextRef.current = context

    return () => {
      context.revert()
    }
  }, dependencies)

  return contextRef
}

// Animation presets
export const animations = {
  fadeIn: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.from(element, {
      opacity: 0,
      y: 20,
      duration: 0.5,
      ease: 'power2.out',
      ...options,
    })
  },

  fadeInUp: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.from(element, {
      opacity: 0,
      y: 40,
      duration: 0.6,
      ease: 'power3.out',
      ...options,
    })
  },

  fadeInScale: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.from(element, {
      opacity: 0,
      scale: 0.9,
      duration: 0.4,
      ease: 'back.out(1.7)',
      ...options,
    })
  },

  slideInLeft: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.from(element, {
      opacity: 0,
      x: -50,
      duration: 0.5,
      ease: 'power2.out',
      ...options,
    })
  },

  slideInRight: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.from(element, {
      opacity: 0,
      x: 50,
      duration: 0.5,
      ease: 'power2.out',
      ...options,
    })
  },

  staggerFadeIn: (
    elements: string | Element[],
    options: gsap.TweenVars = {}
  ) => {
    return gsap.from(elements, {
      opacity: 0,
      y: 30,
      duration: 0.5,
      stagger: 0.1,
      ease: 'power2.out',
      ...options,
    })
  },

  staggerScale: (
    elements: string | Element[],
    options: gsap.TweenVars = {}
  ) => {
    return gsap.from(elements, {
      opacity: 0,
      scale: 0.8,
      duration: 0.4,
      stagger: 0.08,
      ease: 'back.out(1.7)',
      ...options,
    })
  },

  hoverScale: (element: string | Element, options: gsap.TweenVars = {}) => {
    const el = typeof element === 'string' ? document.querySelector(element) : element
    if (!el) return

    gsap.set(el, { transformOrigin: 'center center' })

    el.addEventListener('mouseenter', () => {
      gsap.to(el, {
        scale: 1.05,
        duration: 0.2,
        ease: 'power2.out',
        ...options,
      })
    })

    el.addEventListener('mouseleave', () => {
      gsap.to(el, {
        scale: 1,
        duration: 0.2,
        ease: 'power2.out',
      })
    })
  },

  pulse: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.to(element, {
      scale: 1.05,
      duration: 0.5,
      repeat: -1,
      yoyo: true,
      ease: 'sine.inOut',
      ...options,
    })
  },

  shimmer: (element: string | Element, options: gsap.TweenVars = {}) => {
    return gsap.fromTo(
      element,
      { backgroundPosition: '-200% 0' },
      {
        backgroundPosition: '200% 0',
        duration: 2,
        repeat: -1,
        ease: 'none',
        ...options,
      }
    )
  },
}

// Utility for page transitions
export const pageTransition = {
  enter: (element: string | Element) => {
    return gsap.from(element, {
      opacity: 0,
      y: 20,
      duration: 0.4,
      ease: 'power2.out',
    })
  },

  exit: (element: string | Element) => {
    return gsap.to(element, {
      opacity: 0,
      y: -20,
      duration: 0.3,
      ease: 'power2.in',
    })
  },
}
