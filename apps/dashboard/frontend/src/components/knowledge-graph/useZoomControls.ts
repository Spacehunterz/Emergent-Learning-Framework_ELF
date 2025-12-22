import { useRef, useCallback } from 'react'
import * as d3 from 'd3'

export function useZoomControls() {
  const zoomRef = useRef<d3.ZoomBehavior<SVGSVGElement, unknown> | null>(null)
  const gRef = useRef<d3.Selection<SVGGElement, unknown, null, undefined> | null>(null)
  const currentTransformRef = useRef<d3.ZoomTransform>(d3.zoomIdentity)
  const svgRef = useRef<SVGSVGElement>(null)

  const handleZoomIn = useCallback(() => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      const newTransform = currentTransformRef.current.scale(1.5)
      currentTransformRef.current = newTransform
      gRef.current.transition().duration(300).attr('transform', newTransform.toString())
      svgSelection.call(zoomRef.current.transform, newTransform)
    }
  }, [])

  const handleZoomOut = useCallback(() => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      const newTransform = currentTransformRef.current.scale(0.67)
      currentTransformRef.current = newTransform
      gRef.current.transition().duration(300).attr('transform', newTransform.toString())
      svgSelection.call(zoomRef.current.transform, newTransform)
    }
  }, [])

  const handleResetZoom = useCallback(() => {
    if (svgRef.current && zoomRef.current && gRef.current) {
      const svgSelection = d3.select(svgRef.current)
      currentTransformRef.current = d3.zoomIdentity
      gRef.current.transition().duration(500).attr('transform', d3.zoomIdentity.toString())
      svgSelection.call(zoomRef.current.transform, d3.zoomIdentity)
    }
  }, [])

  return {
    svgRef,
    zoomRef,
    gRef,
    currentTransformRef,
    handleZoomIn,
    handleZoomOut,
    handleResetZoom,
  }
}
