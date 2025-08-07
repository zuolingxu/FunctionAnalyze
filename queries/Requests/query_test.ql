/**
 * @id requests/method-call
 * @name Call to method
 * @description Finds calls to MyClass.methodName
 * @tags call
 *       method
 * @kind problem
 * @problem.severity recommendation
 * @severity recommendation
 */

import python

from AstNode call, PythonFunctionValue method
where
  method.getQualifiedName() = "PreparedRequest.prepare" and
  method.getACall().getNode() = call
select call, call.toString()