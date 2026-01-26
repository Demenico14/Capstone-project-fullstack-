import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { TrendingUp, AlertCircle } from "lucide-react"
import type { YieldEstimate } from "@/lib/api"

interface YieldEstimatesProps {
  estimates: YieldEstimate[]
}

export function YieldEstimates({ estimates }: YieldEstimatesProps) {
  const safeEstimates = Array.isArray(estimates) ? estimates : []

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "A":
        return "bg-green-500"
      case "B":
        return "bg-green-400"
      case "C":
        return "bg-yellow-500"
      case "D":
        return "bg-orange-500"
      case "F":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  if (safeEstimates.length === 0) {
    return (
      <div>
        <h2 className="mb-4 text-2xl font-semibold">Yield Estimates</h2>
        <Card>
          <CardContent className="pt-6">
            <p className="text-center text-muted-foreground">
              No yield estimates available. Collect more sensor data to generate predictions.
            </p>
          </CardContent>
        </Card>
      </div>
    )
  }

  return (
    <div>
      <h2 className="mb-4 text-2xl font-semibold">Yield Estimates</h2>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
        {safeEstimates.map((estimate) => (
          <Card key={estimate.sensor_id}>
            <CardHeader>
              <div className="flex items-center justify-between">
                <CardTitle className="text-lg">{estimate.sensor_id}</CardTitle>
                <Badge className={getGradeColor(estimate.grade)}>Grade {estimate.grade}</Badge>
              </div>
            </CardHeader>
            <CardContent>
              <div className="mb-4">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-sm text-muted-foreground">Yield Score</span>
                  <span className="text-2xl font-bold">{estimate.score}</span>
                </div>
                <div className="h-2 w-full bg-secondary rounded-full overflow-hidden">
                  <div className={`h-full ${getGradeColor(estimate.grade)}`} style={{ width: `${estimate.score}%` }} />
                </div>
              </div>

              <div className="space-y-2">
                <h4 className="text-sm font-semibold">Contributing Factors:</h4>
                <ul className="space-y-1">
                  {estimate.factors.slice(0, 3).map((factor, idx) => (
                    <li key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                      <AlertCircle className="h-3 w-3 mt-0.5 flex-shrink-0" />
                      <span>{factor}</span>
                    </li>
                  ))}
                </ul>
              </div>

              {estimate.recommendations && estimate.recommendations.length > 0 && (
                <div className="mt-4 pt-4 border-t">
                  <h4 className="text-sm font-semibold mb-2">Recommendations:</h4>
                  <ul className="space-y-1">
                    {estimate.recommendations.slice(0, 2).map((rec, idx) => (
                      <li key={idx} className="text-xs text-muted-foreground flex items-start gap-2">
                        <TrendingUp className="h-3 w-3 mt-0.5 flex-shrink-0 text-green-600" />
                        <span>{rec}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
