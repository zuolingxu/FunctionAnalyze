/**
 * @id cpp/examples/function-call-1
 * @name Call to function
 * @description Finds calls to `jsmn_alloc_token`
 * @tags call
 *       function
 *       method
 * @kind problem
 * @problem.severity recommendation
 * @severity recommendation
 */

import cpp

from FunctionCall call, Function fcn
where
  call.getTarget() = fcn and
  // fcn.getDeclaringType().getSimpleName() = "map" and
  // fcn.getDeclaringType().getNamespace().getName() = "std" and
  fcn.hasName("av_int2double")
select call, call.getTarget().getName()
