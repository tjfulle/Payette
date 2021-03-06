! Copyright (2011) Sandia Corporation. Under the terms of Contract
! DE-AC04-94AL85000 with Sandia Corporation, the U.S. Government retains certain
! rights in this software.

! The MIT License

! Copyright (c) Sandia Corporation

! License for the specific language governing rights and limitations under
! Permission is hereby granted, free of charge, to any person obtaining a
! copy of this software and associated documentation files (the "Software"),
! to deal in the Software without restriction, including without limitation
! the rights to use, copy, modify, merge, publish, distribute, sublicense,
! and/or sell copies of the Software, and to permit persons to whom the
! Software is furnished to do so, subject to the following conditions:

! The above copyright notice and this permission notice shall be included
! in all copies or substantial portions of the Software.

! THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
! OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
! FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
! THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
! LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
! FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
! DEALINGS IN THE SOFTWARE.

module tensor_toolkit

  private
  public :: ata, symleaf, dd66x6, push, pull, dp, ddp, mag, dev, tr, iso
  public :: matinv, eigen3x3, zerot, zerov, I6, I9, seedrand, dyad, rot
  public :: unrot, randvec, dp9x6, pullv, pushv, sym_inv, dp6x3, I3x3
  public :: cross, aa2dc, m9t6, rotv, unrotv, reducefac

  ! kind specifiers
  integer, parameter :: sk=selected_real_kind(6), dk=selected_real_kind(14)
  integer, parameter :: fp=dk
  integer, parameter :: ik=selected_int_kind(6)

  ! numbers
  real(kind=fp), parameter :: zero= 0._fp, one=1._fp, two=2._fp, three=3._fp
  real(kind=fp), parameter :: four=4._fp, five=5._fp, six= 6._fp, thirty=30._fp
  real(kind=fp), parameter :: third=one/three, half=one/two
  real(kind=fp), parameter :: root2=1.41421356237309504880168872420969807856967_fp
  real(kind=fp), parameter :: root3=1.73205080756887729352744634150587236694280_fp
  real(kind=fp), parameter :: root6=2.44948974278317809819728407470589139196595_fp
  real(kind=fp), parameter :: toor2=one/root2,toor3=one/root3,toor6=one/root6
  real(kind=fp), parameter :: root23=0.816496580927726032732428024901963797322_fp
  real(kind=fp), parameter :: root32=1.224744871391589049098642037352945695983_fp
  real(kind=fp), parameter :: pi=3.1415926535897932384626433832795028841971694_fp
  real(kind=fp), parameter :: piover6=pi/six
  real(kind=fp), parameter :: huge=1.e50_fp, tiny=1.e-10_fp

  integer, parameter :: diag9(3) = (/1, 5, 9/)
  real(kind=fp), parameter :: &
       I6(6) = (/one, one, one, zero, zero, zero/), &
       zerot(6) = (/zero, zero, zero, zero, zero, zero/), &
       zerov(3) = (/zero, zero, zero/), &
       I9(9) = (/one, zero, zero, zero, one, zero, zero, zero, one/), &
       w(6) = (/one, one, one, two, two, two/)
  real(kind=fp), parameter :: I3x3(3,3) = reshape(I9, shape(I3x3))

  ! mapping from 3x3 to 6x1
  integer, parameter, dimension(3, 3) :: &
       m9t6=reshape((/1, 4, 6, 4, 2, 5, 6, 5, 3/), shape(m9t6))



contains

  function ata(a)
    !---------------------------------------------------------------------------!
    ! Compute Transpose(a).a
    !
    ! Parameters
    ! ----------
    ! a: tensor a stored as 9x1 Voight array
    !
    ! Returns
    ! -------
    ! ata: Symmetric tensor defined by Transpose(a).a stored as 6x1 Voight
    ! array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: ata(6)
    real(kind=fp) :: a(9)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ata
    ata(1) = a(1) * a(1) + a(4) * a(4) + a(7) * a(7)
    ata(2) = a(2) * a(2) + a(5) * a(5) + a(8) * a(8)
    ata(3) = a(3) * a(3) + a(6) * a(6) + a(9) * a(9)
    ata(4) = a(1) * a(2) + a(4) * a(5) + a(7) * a(8)
    ata(5) = a(2) * a(3) + a(5) * a(6) + a(8) * a(9)
    ata(6) = a(1) * a(3) + a(4) * a(6) + a(7) * a(9)
    return
  end function ata

  function symleaf(f)
    !---------------------------------------------------------------------------!
    ! Compute the 6x6 Mandel matrix (with index mapping {11,22,33,12,23,31})
    ! that is the sym-leaf transformation of the input 3x3 matrix F.

    ! If A is any symmetric tensor, and if {A} is its 6x1 Mandel array, then
    ! the 6x1 Mandel array for the tensor B=F.A.Transpose[F] may be computed
    ! by
    !                   {B}=[FF]{A}
    !
    ! If F is a deformation F, then B is the "push" (spatial) transformation
    ! of the reference tensor A. If F is Inverse[F], then B is the "pull"
    ! (reference) transformation of the spatial tensor A, and therefore B
    ! would be Inverse[FF]{A}.

    ! If F is a rotation, then B is the rotation of A, and FF would be be a
    ! 6x6 orthogonal matrix, just as is F.
    !
    ! Parameters
    ! ----------
    ! f: any matrix (in conventional 3x3 storage)
    !
    ! Returns
    ! -------
    ! symleaf: 6x6 Mandel matrix for the sym-leaf transformation matrix
    !
    !
    ! authors
    ! -------
    !  rmb:Rebecca Brannon:theory, algorithm, and code
    !
    ! modification history
    ! --------------------
    !  yymmdd|who|what was done
    !  ------ --- -------------
    !  060915|rmbrann|created routine
    !  120514|tjfulle|conversion to f90
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: f(3, 3)
    real(kind=fp) :: symleaf(6, 6)
    !.......................................................................local
    integer i, j
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~symleaf
    do i = 1, 3
       do j = 1, 3
          symleaf(i, j) = f(i, j) ** 2
       end do
       symleaf(i, 4) = root2 * f(i, 1) * f(i, 2)
       symleaf(i, 5) = root2 * f(i, 2) * f(i, 3)
       symleaf(i, 6) = root2 * f(i, 3) * f(i, 1)
       symleaf(4, i) = root2 * f(1, i) * f(2, i)
       symleaf(5, i) = root2 * f(2, i) * f(3, i)
       symleaf(6, i) = root2 * f(3, i) * f(1, i)
    enddo
    symleaf(4, 4) = f(1, 2) * f(2, 1) + f(1, 1) * f(2, 2)
    symleaf(5, 4) = f(2, 2) * f(3, 1) + f(2, 1) * f(3, 2)
    symleaf(6, 4) = f(3, 2) * f(1, 1) + f(3, 1) * f(1, 2)

    symleaf(4, 5) = f(1, 3) * f(2, 2) + f(1, 2) * f(2, 3)
    symleaf(5, 5) = f(2, 3) * f(3, 2) + f(2, 2) * f(3, 3)
    symleaf(6, 5) = f(3, 3) * f(1, 2) + f(3, 2) * f(1, 3)

    symleaf(4, 6) = f(1, 1) * f(2, 3) + f(1, 3) * f(2, 1)
    symleaf(5, 6) = f(2, 1) * f(3, 3) + f(2, 3) * f(3, 1)
    symleaf(6, 6) = f(3, 1) * f(1, 3) + f(3, 3) * f(1, 1)
    return
  end function symleaf

  function dd66x6(job, a, x)
    !---------------------------------------------------------------------------!
    ! Compute the product of a fourth-order tensor a times a second-order
    ! tensor x (or vice versa if job=-1)
    !              a:x if job=1
    !              x:a if job=-1
    !
    ! Parameters
    ! ----------
    !    a: 6x6 Mandel matrix for a general (not necessarily major-sym)
    !       fourth-order minor-sym matrix
    !    x: 6x6 Voigt matrix
    !
    ! returns
    ! -------
    !    a:x if JOB=1
    !    x:a if JOB=-1
    !
    ! authors
    ! -------
    !  rmb:Rebecca Brannon:theory, algorithm, and code
    !
    ! modification history
    ! --------------------
    !  yymmdd|who|what was done
    !  ------ --- -------------
    !  060915|rmb|created routine
    !  120514|tjfulle|conversion to f90
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer :: job
    real(kind=fp) :: x(6), dd66x6(6)
    real(kind=fp) :: a(6, 6)
    !.......................................................................local
    real(kind=fp), parameter :: &
         mandel(6)=(/one,one,one,root2,root2,root2/)
    real(kind=fp) :: t(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dd66x6

    !  Construct the Mandel version of x
    t = mandel * x

    select case(job)
    case(1)
       ! Compute the Mandel form of A:X
       dd66x6 = matmul(a, t)

    case(-1)
       ! Compute the Mandel form of X:A
       dd66x6 = matmul(t, a)

    case default
       call bombed('unknown job sent to dd66x6')

    end select

    ! Convert result to Voigt form
    dd66x6 = dd66x6 / mandel

    return
  end function dd66x6

  function push(a, f, order)
    !---------------------------------------------------------------------------!
    ! Performs the "push" transformation
    !
    !             1
    !            ---- f.a.Transpose(f)
    !            detf
    !
    ! For example, if a is the Second-Piola Kirchoff stress, then the push
    ! transofrmation returns the Cauchy stress
    !
    ! Parameters
    ! ----------
    !    x: 6x1 Voigt array
    !    f: 9x1 deformation gradient, stored as Voight array
    !
    ! returns
    ! -------
    ! push: 6x1 Voight array
    !
    ! modification history
    ! --------------------
    !  yymmdd|who|what was done
    !  ------ --- -------------
    !  120514|tjfulle|created function
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: push(6)
    real(kind=fp), intent(in) :: a(6), f(9)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: detf, ff(3,3)
    character*1 :: ord
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~push
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    detf = f(1) * f(5) * f(9) + f(2) * f(6) * f(7) + f(3) * f(4) * f(8) &
         -(f(1) * f(6) * f(8) + f(2) * f(4) * f(9) + f(3) * f(5) * f(7))
    ff = reshape(f, shape(ff))
    if (ord == "C" .or. ord == "c") ff = transpose(ff)
    push = one / detf * dd66x6(1, symleaf(ff), a)
    return
  end function push

  function pull(a, f, order)
    !---------------------------------------------------------------------------!
    ! Performs the "pull" transformation
    !
    !            detf * Inverse(f).a.Transpose(Inverse(f))
    !
    ! For example, if a is the Cauchy stress, then the pull transofrmation
    ! returns the second Piola-Kirchoff stress
    !
    ! Parameters
    ! ----------
    !    x: 6x1 Voigt array
    !    f: 9x1 deformation gradient, stored as Voight array
    !
    ! returns
    ! -------
    ! push: 6x1 Voight array
    !
    ! modification history
    ! --------------------
    !  yymmdd|who|what was done
    !  ------ --- -------------
    !  120514|tjfulle|created function
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: pull(6)
    real(kind=fp), intent(in) :: f(9), a(6)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: detf, ff(3,3)
    character*1 :: ord
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~pull
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    detf = f(1) * f(5) * f(9) + f(2) * f(6) * f(7) + f(3) * f(4) * f(8) &
         -(f(1) * f(6) * f(8) + f(2) * f(4) * f(9) + f(3) * f(5) * f(7))
    ff = reshape(f, shape(ff))
    if (ord == "C" .or. ord == "c") ff = transpose(ff)
    pull = detf * dd66x6(1, matinv(symleaf(ff), 6), a)
    return
  end function pull

  function pushv(a, f, flg)
    !---------------------------------------------------------------------------!
    ! Push the vector a forward
    !
    !  If flg == 0
    !      pushv = inv(transpose(f)) . a
    !
    !  else
    !      pushv = 1 / detf * f . a
    !
    !
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer, intent(in) :: flg
    real(kind=fp), intent(in) :: a(3), f(9)
    real(kind=fp) :: pushv(3)
    !.......................................................................local
    real(kind=fp) :: detf, dnom
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~pushv
    if (flg == 0) then
       dnom = f(3) * f(5) * f(7) - f(2) * f(6) * f(7) - f(3) * f(4) * f(8) +  &
              f(1) * f(6) * f(8) + f(2) * f(4) * f(9) - f(1) * f(5) * f(9)
       pushv = (/&
            (a(3) * f(5) * f(7) - a(2) * f(6) * f(7) - a(3) * f(4) * f(8) + &
             a(1) * f(6) * f(8) + a(2) * f(4) * f(9) - a(1) * f(5) * f(9)), &
             !
            -a(3) * f(2) * f(7) + a(3) * f(1) * f(8) + a(2) * f(3) * f(7) - &
             a(2) * f(1) * f(9) - a(1) * f(3) * f(8) + a(1) * f(2) * f(9),  &
             !
             a(3) * f(2) * f(4) - a(2) * f(3) * f(4) - a(3) * f(1) * f(5) + &
             a(1) * f(3) * f(5) + a(2) * f(1) * f(6) - a(1) * f(2) * f(6)/)
       pushv = pushv / dnom
    else
       detf = f(3) * (f(4) * f(8) - f(5) * f(7)) + &
              f(2) * (f(6) * f(7) - f(4) * f(9)) + &
              f(1) * (f(5) * f(9) - f(6) * f(8))
       pushv = one / detf * (/a(1) * f(1) + a(2) * f(2) + a(3) * f(3), &
                              a(1) * f(4) + a(2) * f(5) + a(3) * f(6), &
                              a(1) * f(7) + a(2) * f(8) + a(3) * f(9)/)
    end if
  end function pushv

  function pullv(a, f, flg)
    !---------------------------------------------------------------------------!
    ! Pull the vector a back
    !
    ! If flg == 0
    !      pullv = transpose(f) . a
    !
    ! else
    !      pullv = detf * inv(f) . a
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer, intent(in) :: flg
    real(kind=fp), intent(in) :: a(3)
    real(kind=fp), intent(in) :: f(9)
    real(kind=fp) :: pullv(3)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~pullv
    if (flg == 0) then
       pullv = (/a(1) * f(1) + a(2) * f(4) + a(3) * f(7), &
                 a(1) * f(2) + a(2) * f(5) + a(3) * f(8), &
                 a(1) * f(3) + a(2) * f(6) + a(3) * f(9)/)
    else
       pullv = (/a(3) * (f(2) * f(6) - f(3) * f(5)) + &
                 a(2) * (f(3) * f(8) - f(2) * f(9)) + &
                 a(1) * (f(5) * f(9) - f(6) * f(8)), &
                 !
                 a(3) * (f(3) * f(4) - f(1) * f(6)) + &
                 a(2) * (f(1) * f(9) - f(3) * f(7)) + &
                 a(1) * (f(6) * f(7) - f(4) * f(9)), &
                 !
                 a(3) * (f(1) * f(5) - f(2) * f(4)) + &
                 a(2) * (f(2) * f(7) - f(1) * f(8)) + &
                 a(1) * (f(4) * f(8) - f(5) * f(7))/)
    end if
  end function pullv

  function unrot(a, r, order)
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: unrot(6)
    real(kind=fp), intent(in) :: a(6), r(9)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: rr(3,3)
    character*1 :: ord
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~unrot
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    rr = reshape(r, shape(rr))
    if (ord == "C" .or. ord == "c") rr = transpose(rr)
    unrot = dd66x6(1, symleaf(transpose(rr)), a)
    return
  end function unrot

  function rot(a, r, order)
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: rot(6)
    real(kind=fp), intent(in) :: a(6), r(9)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: rr(3, 3)
    character*1 :: ord
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~rot
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    rr = reshape(r, shape(rr))
    if (ord == "C" .or. ord == "c") rr = transpose(rr)
    rot = dd66x6(1, symleaf(rr), a)
    return
  end function rot

  function rotv(v, r, order)
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: rotv(3)
    real(kind=fp), intent(in) :: v(3), r(9)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: rr(3, 3)
    character*1 :: ord
    ! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ rotv
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    rr = reshape(r, shape(rr))
    if (ord == "C" .or. ord == "c") rr = transpose(rr)
    rotv = matmul(rr, v)
    return
  end function rotv

  function unrotv(v, r, order)
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: unrotv(3)
    real(kind=fp), intent(in) :: v(3), r(9)
    character*1, intent(in), optional :: order
    !.......................................................................local
    real(kind=fp) :: rr(3, 3)
    character*1 :: ord
    ! ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ unrotv
    if (present(order)) then
       ord = order
    else
       ord = "F"
    end if
    rr = reshape(r, shape(rr))
    if (ord == "C" .or. ord == "c") rr = transpose(rr)
    unrotv = matmul(transpose(rr), v)
    return
  end function unrotv

  function inv(a)
    !---------------------------------------------------------------------------!
    ! compute the inverse of a.
    !
    ! Parameters
    ! ----------
    ! a: 3x3 matrix stored as 9x1 array
    !
    ! Returns
    ! -------
    ! inv: inverse of a stored as 9x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: inv(9)
    real(kind=fp), intent(in) :: a(9)
    real(kind=fp) :: det
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~rot
    det = a(1) * a(5) * a(9) + a(2) * a(6) * a(7) + a(3) * a(4) * a(8) &
        -(a(1) * a(6) * a(8) + a(2) * a(4) * a(9) + a(3) * a(5) * a(7))
    if (abs(det) < epsilon(det)) call bombed('det == 0')
    inv = (/a(5) * a(9) - a(8) * a(6), &
            a(8) * a(3) - a(2) * a(9), &
            a(2) * a(6) - a(5) * a(3), &
            a(6) * a(7) - a(9) * a(4), &
            a(9) * a(1) - a(3) * a(7), &
            a(3) * a(4) - a(6) * a(1), &
            a(4) * a(8) - a(7) * a(5), &
            a(7) * a(2) - a(1) * a(8), &
            a(1) * a(5) - a(4) * a(2)/)
    inv = inv / det
    return
  end function inv

  function sym_inv(a)
    !---------------------------------------------------------------------------!
    ! compute the inverse of a.
    !
    ! Parameters
    ! ----------
    ! a: 3x3 matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! inv: inverse of a stored as 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: det
    real(kind=fp) :: a(6), sym_inv(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~sym_inv
    det = a(1) * a(2) * a(3) - a(3) * a(4) ** 2 - a(1) * a(5) ** 2 &
          + two * a(4) * a(5) * a(6) - a(2) * a(6) ** 2
    sym_inv = (/a(2) * a(3) - a(5) ** 2, &
                a(1) * a(3) - a(6) ** 2, &
                a(1) * a(2) - a(4) ** 2, &
                -(a(3) * a(4)) + a(5) * a(6), &
                -(a(1) * a(5)) + a(4) * a(6), &
                a(4) * a(5) - a(2) * a(6)/)
    sym_inv = sym_inv / det
    return
  end function sym_inv

  function dp9x6(a, b)
    !---------------------------------------------------------------------------!
    ! compute the dot product a.b
    !
    ! Parameters
    ! ----------
    ! a: 3x3 matrix stored as 9x1 array
    ! b: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! dp9x6: a.b stored as a 9x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: a(9), dp9x6(9)
    real(kind=fp) :: b(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dp9x6
    dp9x6 = (/a(1) * b(1) + a(4) * b(4) + a(7) * b(6), &
              a(4) * b(2) + a(1) * b(4) + a(7) * b(5), &
              a(7) * b(3) + a(4) * b(5) + a(1) * b(6), &
              a(2) * b(1) + a(5) * b(4) + a(8) * b(6), &
              a(5) * b(2) + a(2) * b(4) + a(8) * b(5), &
              a(8) * b(3) + a(5) * b(5) + a(2) * b(6), &
              a(3) * b(1) + a(6) * b(4) + a(9) * b(6), &
              a(6) * b(2) + a(3) * b(4) + a(9) * b(5), &
              a(9) * b(3) + a(6) * b(5) + a(3) * b(6)/)
    return
  end function dp9x6

  function ddp(a, b)
    !---------------------------------------------------------------------------!
    ! compute the double dot product a:b
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    ! b: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! ddp: a:b
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: ddp
    real(kind=fp) :: a(6), b(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ddp
    ddp = sum(w * a * b)
    return
  end function ddp

  function dp(a, b)
    !---------------------------------------------------------------------------!
    ! compute the dot product a.b
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    ! b: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! dp: a.b stored as a 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: dp(6)
    real(kind=fp) :: a(6), b(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dp
    dp = (/ &
         a(1) * b(1) + a(4) * b(4) + a(6) * b(6), &
         a(2) * b(2) + a(4) * b(4) + a(5) * b(5), &
         a(3) * b(3) + a(5) * b(5) + a(6) * b(6), &
         a(4) * b(2) + a(1) * b(4) + a(6) * b(5), &
         a(5) * b(3) + a(2) * b(5) + a(4) * b(6), &
         a(6) * b(3) + a(4) * b(5) + a(1) * b(6) /)
    return
  end function dp

  function dp6x3(a, b)
    !---------------------------------------------------------------------------!
    ! compute the a.b
    !
    ! Parameters
    ! ----------
    ! a: symmetric 3x3 matrix stored as 6x1 array
    ! b: 3x1 array
    !
    ! Returns
    ! -------
    ! dp6x3: 3x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: a(6)
    real(kind=fp) :: b(3), dp6x3(3)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dp6x3
    dp6x3 = (/a(1) * b(1) + a(4) * b(2) + a(6) * b(3), &
              a(4) * b(1) + a(2) * b(2) + a(5) * b(3), &
              a(6) * b(1) + a(5) * b(2) + a(3) * b(3)/)
    return
  end function dp6x3

  function dyad(a, b)
    !---------------------------------------------------------------------------!
    ! compute the dyadic product axb
    !
    ! Parameters
    ! ----------
    ! a: 3x1 array
    ! b: 3x1 array
    !
    ! Returns
    ! -------
    ! dyad: 3x3 symmetric matrix stored as 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: a(3), b(3)
    real(kind=fp) :: dyad(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dp6x3
    dyad = (/a(1) * b(1), a(2) * b(2), a(3) * b(3), &
             a(1) * b(2), a(2) * b(3), a(1) * b(3)/)
    return
  end function dyad

  function mag(a)
    !---------------------------------------------------------------------------!
    ! compute the magnitude of a
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! mag: sqrt(a:a) stored as a 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) mag
    real(kind=fp) :: a(6)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~mag
    mag = sqrt(ddp(a, a))
    return
  end function mag

  function dev(a)
    !---------------------------------------------------------------------------!
    ! compute the deviatoric part of a
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! dev: deviatoric part of a stored as a 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: dev(6), a(6)
    real(kind=fp) :: trdev
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~dev
    dev = a - iso(a)
    trdev = -sum(dev(1:3)) / three
    dev(1) = dev(1) + trdev
    dev(2) = dev(2) + trdev
    dev(3) = -(dev(1) + dev(2))
    return
  end function dev

  function iso(a)
    !---------------------------------------------------------------------------!
    ! compute the isotropic part of a
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! iso: isotropic part of a stored as a 6x1 array
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: iso(6), a(6)
    !.......................................................................local
    real(kind=fp) :: tra
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~iso
    tra = sum(a(1:3))
    if (abs(tra) < epsilon(tra)) tra = zero
    iso = tra / three * I6
    return
  end function iso

  function tr(a)
    !---------------------------------------------------------------------------!
    ! compute the trace of a
    !
    ! Parameters
    ! ----------
    ! a: 3x3 symmetric matrix stored as 6x1 array
    !
    ! Returns
    ! -------
    ! tr: trace of a
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: a(6)
    real(kind=fp) :: tr
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~iso
    tr = sum(a(1:3))
    if (abs(tr) < epsilon(tr)) tr = zero
    return
  end function tr

  function matinv(a, n)
    !---------------------------------------------------------------------------!
    ! This procedure computes the inverse of a real, general matrix using
    ! Gauss- Jordan elimination with partial pivoting. The input matrix, A, is
    ! returned unchanged, and the inverted matrix is returned in matinv. The
    ! procedure also returns an integer flag, icond, indicating whether A is
    ! well- or ill- conditioned. If the latter, the contents of matinv will be
    ! garbage.
    !
    ! The logical dimensions of the matrices A(1:n,1:n) and matinv(1:n,1:n)
    ! are assumed to be the same as the physical dimensions of the storage
    ! arrays a(1:np,1:np) and matinv(1:np,1:np), i.e., n = np. If A is not
    ! needed, a and matinv can share the same storage locations.
    !
    ! Parameters
    ! ----------
    ! A: real  matrix to be inverted
    ! n: int   number of rows/columns
    !
    ! Returns
    ! -------
    ! matinv   real  inverse of A
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer :: n
    real(kind=fp) :: a(n, n), matinv(n, n)
    !.......................................................................local
    integer :: row, col, icond
    integer :: v(1)
    real(kind=fp) :: wmax, fac, wcond=1.d-13
    real(kind=fp) :: dum(n)
    real(kind=fp) :: w(n, n)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~matinv

    ! Initialize

    icond = 0
    matinv  = zero
    do row = 1, n
       matinv(row, row) = one
    end do
    w = a
    do row = 1, n
       v = maxloc(abs(w(row,:)))
       wmax = w(row, v(1))
       if (Wmax == 0) then
          icond = 1
          return
       end if
       w(row, :) = w(row, :) / wmax
       matinv(row, :) = matinv(row, :) / wmax
    end do

    ! Gauss-Jordan elimination with partial pivoting

    do col = 1, n
       v = maxloc(abs(w(col:, col)))
       row = v(1) + col - 1
       dum(col:) = w(col, col:)
       w(col, col:) = w(row, col:)
       w(row, col:) = dum(col:)
       dum(:) = matinv(col, :)
       matinv(col, :) = matinv(row, :)
       matinv(row, :) = dum(:)
       wmax = w(col, col)
       if (abs(wmax) < wcond) then
          icond = 1
          return
       end if
       row = col
       w(row,col:) = w(row, col:) / wmax
       matinv(row, :) = matinv(row, :) / wmax
       do row = 1, n
          if (row == col) cycle
          fac = w(row, col)
          w(row, col:) = w(row, col:) - fac * w(col, col:)
          matinv(row, :) = matinv(row, :) - fac * matinv(col, :)
       end do
    end do

    return

  end function matinv

  subroutine eigen3x3(job, a, n, eval, proj, r, t, z )
    !---------------------------------------------------------------------------!
    ! compute eigenvalues and eigenprojectors (or eigenvectors if job > 0) for
    ! a symmetric 3x3 matrix a
    !
    ! Parameters
    ! ----------
    !   job : in, int
    !     flag to indicate whether eigenprojectors are desired.
    !        = 0 if only invariants and eigenvalues are desired
    !     otherwise, eigenprojectors will also be found
    !        = 1 if method 1 is to be used for eigenprojectors
    !        = 2 if method 2 is to be used for eigenprojectors
    !     Both methods should give identical results, so this is purely a
    !     matter of preference. Eventually timing studies should be done to
    !     assess which method does best. Method 2 has the advantage of
    !     computing the Lode Cartesian basis as an intermediate result, which
    !     could be returned as an output by modifying the args of this routine
    !     appropriately.
    !   a : in, array
    !     the symmetric 3x3 matrix to be analyzed. Components must be sent in
    !     a single Voigt array with components ordered {11, 22, 33, 12, 23, 31}
    !   n : out, int
    !     equal in absolute value to number of distinct eigenvalues if there
    !     are two distinct eigenvalues, N=2 if the single root is larger than
    !     the double root and N=-2 if the single root is smaller than the
    !     double root.
    !   eval : out, array
    !     eigenvalues, ordered from low to high
    !   proj : out, array
    !     inflated eigenprojectors (depending on JOB)
    !        JOB=0: projectors are not computed
    !        JOB=1 or 2: PROJ(i,j) is the ith Voigt component of the jth
    !                    eigenprojector.
    !    r : out, float
    !      Lode radius
    !    t : out, float
    !      Lode angle
    !    z : out, float
    !      Lode axial coordinate
    !
    ! History
    ! -------
    ! 2004.01.11:Rebecca Brannon:devised and coded algorithm
    ! 2012.05.30:Tim Fuller:converted to f90
    !
    ! Notes
    ! -----
    ! A projector is a 3x3 tensor P satisfying P.P=P For example, the
    ! identity matrix is, trivially, a projector. Any diagonal matrix with
    ! ones or zeros on the diagonal is a projector. Any fully populated
    ! matrix whose eigenvalues are all either zero or one is a projector. The
    ! rank of a projector is the number of eigenvalues equal to 1. The rank
    ! of a projector (which may be readily found by its trace) equals the
    ! dimension of the eigenspace associated with an eigenvalue. If desired,
    ! eVECs may be found by performing Gram-Schmidt orthogonalization (GSO)
    ! on the columns (or rows) of an eigenprojector. The identity matrix is
    ! the only rank 3 projector. A rank 2 projector P has two eigenvalues
    ! equal to 1 and the associated eigenvectors are not unique -- they
    ! merely need to lie within a given plane.
    !
    ! For a rank 2 projector, P, the operation P.x will return the part of the
    ! vector x in the plane. A rank 1 projector, has only one eigenvalue equal
    ! to 1 and the operation P.x returns the part of any vector x in the
    ! direction of the eigenvector.
    !
    ! Any fully populated matrix [A] may be decomposed as follows:
    !
    ! If [A] has one distinct eigenvalue, eval, then
    !        [A] = eval I
    ! Note, that the identity I is a rank 3 projector
    !
    ! If [A] has two distinct eigenvalues, eval1 and eval2, then
    !        [A] = eval1 [P1] + eval2 [P2]
    ! where [P1] and [P2] are projectors, one being rank 1 and the other rank 2.
    !
    ! If [A] has three distinct eigenvalues, then
    !        [A] = eval1 [P1] + eval2 [P2] + eval3 [P3]
    ! where [P1], [P2], and [P3]  are rank 1 projectors.
    !
    ! This subroutine algebraically determines the high, medium, and low
    ! eigenvalues and their associated eigenprojectors. The procedure requires
    ! identifying the number of distinct eigenvalues, and this can be done
    ! PRIOR TO actually finding the eigenvalues themselves. Four cases must be
    ! considered separately:
    !
    ! MMM: the middle eigenvalue has multiplicity 3, implying that there is
    !      only one distinct eigenvalue (N=1)
    !
    ! MMH: the middle eigenvalue has multiplicity 2 and is smaller than the
    !      other eigenvalue (N=2)
    !
    ! LMM: the middle eigenvalue has multiplicity 2 and is larger than the
    !      other eigenvalue (N=-2)
    !
    ! LMH: the middle eigenvalue has multiplicity 1, implying that there are
    !      three distinct eigenvalues (N=3).
    !
    ! It can be shown that the eigenprojectors corresponding to distinct
    ! eigenvalues are themselves unique and distinct. In this code, P(i,k)
    ! denotes the ith component of the kth eigenprojector, where i ranges from
    ! 1 to 6 (components of a symmetric matrix) and k ranges from 1 to 3,
    ! corresponding to the eigenvalues ordered such that eval(1) .le. eval(2)
    ! .le. eval(3). when the middle eigenvalue, eval(2) has multiplicity, its
    ! eigen projector is saved in PROJ(i,2) and the other eigenprojector
    ! associated with the repeated eigenvalue is simple set to zero. For
    ! example, in case LMM, only P(i,1) and P(i,2) will have some nonzero
    ! components. By zeroing out "spare" eigenprojectors associated with the
    ! middle eigenvalue, the matrix can always be written in inflated spectral
    ! form as
    !
    !     [A] = eval1 [P1] + eval2 [P2] + eval3 [P3]
    !
    ! Upon return from the routine, you have two ways to determine the rank of
    ! a projector. You can use the returned value of N, or you can compute the
    ! rank on the fly by
    !
    !     rank[P] = NINT(trace[P])
    !
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer :: n, job
    real(kind=fp) :: p, ri1, rj2, rj3, r, t, z
    real(kind=fp) :: a(6)
    real(kind=fp) :: eval(3)
    real(kind=fp) :: proj(6, 3)
    !.......................................................................local
    integer :: i, j, k
    real(kind=fp) sint,sin2t,sin3t
    real(kind=fp) cost,cos2t,cos3t
    real(kind=fp) amag,sss
    real(kind=fp) dum,rrr
    real(kind=fp) :: uval(3)
    real(kind=fp) ::u(6), v(6), x(6), y(6)
    !..........................................................statement function
    ! Define a statement function zerro(realnum) that returns "TRUE" if
    ! realnum equals zero to within machine precision and allowable round-off.
    ! Typically, machine precision is around 1.e-20 and calculations -- even
    ! analytical -- tend to be accurate to within 1.e-16. Thus, the allowable
    ! round-off allowance is roa=1.e-4.
    real(kind=fp), parameter :: roa=1.d-4
    real(kind=fp) :: realnum
    logical*8 :: zerro
    zerro(realnum) = ((abs(realnum) * roa + one) - one == zero)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~eigen3x3
    proj = zero

    ! first invariant, mean of diagonals,  and Lode axial coordinate
    ri1 = a(1)+a(2)+a(3)
    p=ri1*third
    z = ri1*toor3

    ! compute deviator
    v(1)=a(1)-p
    v(2)=a(2)-p
    v(3)=a(3)-p
    v(4)=a(4)
    v(5)=a(5)
    v(6)=a(6)
    ! manage round-off by re-deviating the deviator
    dum=-(v(1)+v(2)+v(3))*third
    v(1)=v(1)+dum
    v(2)=v(2)+dum
    v(3)=v(3)+dum
    v(4)=v(4)
    v(5)=v(5)
    v(6)=v(6)
    v(2)=-(v(1)+v(3))
    ! Compute J2=(1/2) tr[A'.A'] = (1/2) tr[V.V] This also equals the negative
    ! second characteristic invariant of [V] is deviatoric. Also compute Lode
    ! radius R = L2 norm of deviator
    rj2 =  v(4)**2 + v(5)**2 + v(6)**2 &
         - ( v(1)*v(2)  +  v(2)*v(3)  +  v(3)*v(1))
    r=root2*sqrt(rj2)

    ! L2 norm of the [A] matrix (used to make relative comparisons)
    amag=sqrt(r*r+z*z)

    !******************************************************************* MMM
    if (amag.eq.zero.or.zerro(r/amag)) then
       ! The matrix is isotropic
       n=1                  !number of distinct eigenvalues
       eval(2)=toor3*z      !the eigenvalue
       eval(1)=eval(2)
       eval(3)=eval(2)
       uval(1)=-toor2
       uval(2)= zero
       uval(3)= toor2
       t=zero               !without loss, set Lode angle = 0.0
       sin3t=zero
       cos3t=one
       rj3=zero
       do i=1,6
          u(i)=zero
       enddo

       if (job.eq.0) return
       proj(1,2)=one        !Eigenprojector is just the identity
       proj(2,2)=one
       proj(3,2)=one
       go to 999

    end if

    ! To reach this point, the matrix is not isotropic (R.ne.0).

    ! compute unit tensor U in the direction of deviator
    ! This is the tensor S_hat in the published algorithm
    dum=one/r
    u(1)=v(1)*dum
    u(2)=v(2)*dum
    u(3)=v(3)*dum
    u(4)=v(4)*dum
    u(5)=v(5)*dum
    u(6)=v(6)*dum
    ! Manage round-off for cases where R is extremely small
    ! by re-normalizing this already normalized tensor
    dum =one/(root2*sqrt(  u(4)**2 + u(5)**2 + u(6)**2 &
         - ( u(1)*u(2)  +  u(2)*u(3)  +  u(3)*u(1))))
    u(1)=u(1)*dum
    u(2)=u(2)*dum
    u(3)=u(3)*dum
    u(4)=u(4)*dum
    u(5)=u(5)*dum
    u(6)=u(6)*dum

    ! compute sine of three times the Lode angle
    dum=   u(1)*u(2)*u(3) + two*u(4)*u(5)*u(6) &
         - (u(1)*u(5)*u(5) + u(2)*u(6)*u(6) + u(3)*u(4)*u(4))
    rj3 = dum * (r**3)
    sin3t=min(max(three*root6*dum,-one),one)

    !******************************************************************* MMH
    if (zerro(one-sin3t)) then
       ! To get inside this if-block, the middle eigenvalue must equal the
       ! low eigenvalue, and the high eigenvalue is distinct.
       n=2                              ! number of distinct eigenvalues
       t=piover6                        ! Lode angle
       uval(1)= -toor6
       uval(2)= -toor6
       uval(3)= root23
       eval(3)=p+uval(3)*r              ! high eigenvalue
       eval(2)=p+uval(2)*r              ! middle eigenvalue
       eval(1)=eval(2)                  ! "low" eval = middle eval

       if (job.eq.0) return
       proj(1,3) = (one+root6*u(1))*third   ! 11 component of PH
       proj(2,3) = (one+root6*u(2))*third   ! 22 component of PH
       proj(3,3) = (one+root6*u(3))*third   ! 33 component of PH
       proj(4,3) =     (root6*u(4))*third   ! 12 component of PH
       proj(5,3) =     (root6*u(5))*third   ! 23 component of PH
       proj(6,3) =     (root6*u(6))*third   ! 31 component of PH

       proj(1,2) = one-proj(1,3)            ! 11 component of PM
       proj(2,2) = one-proj(2,3)            ! 22 component of PM
       proj(3,2) = one-proj(3,3)            ! 33 component of PM
       proj(4,2) =    -proj(4,3)            ! 12 component of PM
       proj(5,2) =    -proj(5,3)            ! 23 component of PM
       proj(6,2) =    -proj(6,3)            ! 31 component of PM
       go to 999

       !******************************************************************* LMM
    else if (zerro(one+sin3t)) then         ! LMM
       ! To get inside this if-block, the middle eigenvalue must equal the
       ! high eigenvalue, and the low eigenvalue is distinct.
       n=-2                              !-number of distinct eigenvalue
       t=-piover6                        ! Lode angle
       uval(1)= -root23
       uval(2)=  toor6
       uval(3)=  toor6
       eval(1)=p+uval(1)*r               ! low eigenvalue
       eval(2)=p+uval(2)*r               ! middle eigenvalue
       eval(3)=eval(2)                   ! "high" eval = middle eval
       if (job.eq.0) return
       proj(1,1) = (one-root6*u(1))*third   ! 11 component of PH
       proj(2,1) = (one-root6*u(2))*third   ! 22 component of PH
       proj(3,1) = (one-root6*u(3))*third   ! 33 component of PH
       proj(4,1) =     (root6*u(4))*third   ! 12 component of PH
       proj(5,1) =     (root6*u(5))*third   ! 23 component of PH
       proj(6,1) =     (root6*u(6))*third   ! 31 component of PH

       proj(1,2) = one-proj(1,1)            ! 11 component of PM
       proj(2,2) = one-proj(2,1)            ! 22 component of PM
       proj(3,2) = one-proj(3,1)            ! 33 component of PM
       proj(4,2) =    -proj(4,1)            ! 12 component of PM
       proj(5,2) =    -proj(5,1)            ! 23 component of PM
       proj(6,2) =    -proj(6,1)            ! 31 component of PM
       go to 999
    end if

    !******************************************************************* LMH
    ! To reach this point, there must be three distinct eigenvalues
    n=3                    ! number of distinct eigenvalues
    t=third*asin(sin3t)    ! principal Lode angle
    cost=cos(t)
    sint=sin(t)
    cos3t=min(sqrt(max(one-sin3t*sin3t,zero)),one)

    ! eigenvalues
    rrr=toor2*r
    sss=toor3*sint
    uval(1)=toor2*(sss-cost)  !low
    uval(2)=-root2*sss        !middle
    uval(3)=toor2*(sss+cost)  !high

    ! Manage round-off by making absolutely sure these evals
    ! sum to zero and form a unit vector.
    dum=-third*(uval(1)+uval(2)+uval(3))
    uval(1)=uval(1)+dum
    uval(2)=uval(2)+dum
    uval(3)=uval(3)+dum
    uval(2)=-(uval(1)+uval(3))
    dum=one/sqrt(uval(1)*uval(1)+uval(2)*uval(2)+uval(3)*uval(3))
    uval(1)=uval(1)*dum
    uval(2)=uval(2)*dum
    uval(3)=uval(3)*dum

    eval(1)=p+uval(1)*r              ! low eigenvalue
    eval(2)=p+uval(2)*r              ! middle eigenvalue
    eval(3)=p+uval(3)*r              ! high eigenvalue

    if (job.eq.0) return
    if (job.eq.1) then
       ! get eigenprojectors using method 1
       i=1
       j=2
       k=3
       v(1)=u(1)-uval(i)
       v(2)=u(2)-uval(i)
       v(3)=u(3)-uval(i)
       dum=one/((uval(j)-uval(i))*(uval(k)-uval(i)))
       proj(1,i) = dum*(v(2)*v(3)-u(5)*u(5)) ! 11 component of PL
       proj(2,i) = dum*(v(3)*v(1)-u(6)*u(6)) ! 22 component of PL
       proj(3,i) = dum*(v(1)*v(2)-u(4)*u(4)) ! 33 component of PL
       proj(4,i) = dum*(u(5)*u(6)-v(3)*u(4)) ! 12 component of PL
       proj(5,i) = dum*(u(6)*u(4)-v(1)*u(5)) ! 23 component of PL
       proj(6,i) = dum*(u(4)*u(5)-v(2)*u(6)) ! 31 component of PL
       i=2
       j=3
       k=1
       v(1)=u(1)-uval(i)
       v(2)=u(2)-uval(i)
       v(3)=u(3)-uval(i)
       dum=one/((uval(j)-uval(i))*(uval(k)-uval(i)))
       proj(1,i) = dum*(v(2)*v(3)-u(5)*u(5)) ! 11 component of PM
       proj(2,i) = dum*(v(3)*v(1)-u(6)*u(6)) ! 22 component of PM
       proj(3,i) = dum*(v(1)*v(2)-u(4)*u(4)) ! 33 component of PM
       proj(4,i) = dum*(u(5)*u(6)-v(3)*u(4)) ! 12 component of PM
       proj(5,i) = dum*(u(6)*u(4)-v(1)*u(5)) ! 23 component of PM
       proj(6,i) = dum*(u(4)*u(5)-v(2)*u(6)) ! 31 component of PM
       i=3
       j=1
       k=2
       v(1)=u(1)-uval(i)
       v(2)=u(2)-uval(i)
       v(3)=u(3)-uval(i)
       dum=one/((uval(j)-uval(i))*(uval(k)-uval(i)))
       proj(1,i) = dum*(v(2)*v(3)-u(5)*u(5)) ! 11 component of PH
       proj(2,i) = dum*(v(3)*v(1)-u(6)*u(6)) ! 22 component of PH
       proj(3,i) = dum*(v(1)*v(2)-u(4)*u(4)) ! 33 component of PH
       proj(4,i) = dum*(u(5)*u(6)-v(3)*u(4)) ! 12 component of PH
       proj(5,i) = dum*(u(6)*u(4)-v(1)*u(5)) ! 23 component of PH
       proj(6,i) = dum*(u(4)*u(5)-v(2)*u(6)) ! 31 component of PH
    else
       ! compute a unit tensor in the direction of the deviatoric part of U^2
       ! This is then tensor called T_hat in the published documentation
       v(1) = root6*(u(1)**2 + u(4)**2 + u(6)**2 - third)
       v(2) = root6*(u(2)**2 + u(5)**2 + u(4)**2 - third)
       v(3) = root6*(u(3)**2 + u(6)**2 + u(5)**2 - third)
       v(4) = root6*(u(6)*u(5) - u(4)*u(3))
       v(5) = root6*(u(4)*u(6) - u(5)*u(1))
       v(6) = root6*(u(5)*u(4) - u(6)*u(2))

       ! By the way, u is a unit tensor in the direction of Adev and it
       ! therefore is like a radial base tensor. The angular base tensor is
       ! given by v -sin3t u In future versions, it might be useful to
       ! plasticity models to return this angular base tensor.

       ! compute the Cartesian Lode base tensors
       !       X() is called B1 in the published documentation
       !       Y() is called B2 in the published documentation
       cos2t=cos(two*t)
       sin2t=sin(two*t)
       cos3t=min(sqrt(max(one-sin3t*sin3t,zero)),one)
       dum=one/cos3t

       x(1)=(cos2t*u(1)-sint*v(1))*dum
       x(2)=(cos2t*u(2)-sint*v(2))*dum
       x(3)=(cos2t*u(3)-sint*v(3))*dum
       x(4)=(cos2t*u(4)-sint*v(4))*dum
       x(5)=(cos2t*u(5)-sint*v(5))*dum
       x(6)=(cos2t*u(6)-sint*v(6))*dum

       y(1)=(-sin2t*u(1)+cost*v(1))*dum
       y(2)=(-sin2t*u(2)+cost*v(2))*dum
       y(3)=(-sin2t*u(3)+cost*v(3))*dum
       y(4)=(-sin2t*u(4)+cost*v(4))*dum
       y(5)=(-sin2t*u(5)+cost*v(5))*dum
       y(6)=(-sin2t*u(6)+cost*v(6))*dum

       proj(1,3)=third+toor2*x(1)+toor6*y(1) ! 11 component of PH
       proj(2,3)=third+toor2*x(2)+toor6*y(2) ! 22 component of PH
       proj(3,3)=third+toor2*x(3)+toor6*y(3) ! 33 component of PH
       proj(4,3)=      toor2*x(4)+toor6*y(4) ! 12 component of PH
       proj(5,3)=      toor2*x(5)+toor6*y(5) ! 23 component of PH
       proj(6,3)=      toor2*x(6)+toor6*y(6) ! 31 component of PH

       proj(1,2)=third-root23*y(1)           ! 11 component of PM
       proj(2,2)=third-root23*y(2)           ! 22 component of PM
       proj(3,2)=third-root23*y(3)           ! 33 component of PM
       proj(4,2)=     -root23*y(4)           ! 12 component of PM
       proj(5,2)=     -root23*y(5)           ! 23 component of PM
       proj(6,2)=     -root23*y(6)           ! 31 component of PM

       proj(1,1)=third-toor2*x(1)+toor6*y(1) ! 11 component of PL
       proj(2,1)=third-toor2*x(2)+toor6*y(2) ! 22 component of PL
       proj(3,1)=third-toor2*x(3)+toor6*y(3) ! 33 component of PL
       proj(4,1)=     -toor2*x(4)+toor6*y(4) ! 12 component of PL
       proj(5,1)=     -toor2*x(5)+toor6*y(5) ! 23 component of PL
       proj(6,1)=     -toor2*x(6)+toor6*y(6) ! 31 component of PL

       ! Note: it would be computationally more efficient to instead compute
       ! PL by I-PH-PM, but this routine is currently written to verify
       ! published formulas. To enable the more efficient computation, comment
       ! out the PL calculation above and uncomment the one below:
       ! PROJ(1,1)=ONE-PROJ(1,3)-PROJ(1,2)     ! 11 component of PL
       ! PROJ(2,1)=ONE-PROJ(2,3)-PROJ(2,2)     ! 22 component of PL
       ! PROJ(3,1)=ONE-PROJ(3,3)-PROJ(3,2)     ! 33 component of PL
       ! PROJ(4,1)=   -PROJ(4,3)-PROJ(4,2)     ! 12 component of PL
       ! PROJ(5,1)=   -PROJ(5,3)-PROJ(5,2)     ! 23 component of PL
       ! PROJ(6,1)=   -PROJ(6,3)-PROJ(6,2)     ! 31 component of PL
    end if

999 continue
    return
  end subroutine eigen3x3

  subroutine proj2evec(n,proj,evec)
    !---------------------------------------------------------------------------!
    ! compute eigenvectors from inflated eigenprojectors. The 3x3 matrix EVEC
    ! is the direction cosine matrix such that
    !
    !           [A] = [Q] . [lambda] . [Q]^T
    !
    ! Parameters
    ! ----------
    ! n : in, int
    !   eigenvalue multiplicity flag sent as output from eigen3x3
    ! evec : out, array
    !   matrix whose columns contain the eigenvectors in other words,
    !   EVEC(i,j) = ith component of the eigenvector associated with the jth
    !   eigenvalue. Because these eigenvectors are found from eigenprojectors,
    !   they will have unique affinity with the laboratory basis.
    !
    ! History
    ! -------
    ! 2004.01.26:Rebecca Brannon:devised and coded algorithm
    ! 2012.05.30:Tim Fuller:converted to f90
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer :: n
    real(kind=fp) :: proj(6, 3)
    real(kind=fp) :: evec(3, 3)
    !.......................................................................local
    real(kind=fp) :: duma(3)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~proj2evec
    if (n.eq.1) then     ! MMM
       call affinity(3,proj(1,2),evec(1,1),evec(1,2),evec(1,3))
    else if (n.eq.2) then  ! MMH
       call affinity(2,proj(1,2),evec(1,1),evec(1,2),duma)
       call affinity(1,proj(1,3),evec(1,3),duma,duma)
    else if (n.eq.-2) then ! LMM
       call affinity(1,proj(1,1),evec(1,1),duma,duma)
       call affinity(2,proj(1,2),evec(1,2),evec(1,3),duma)
    else if (n.eq.3) then  ! LMH
       call affinity(1,proj(1,1),evec(1,1),duma,duma)
       call affinity(1,proj(1,2),evec(1,2),duma,duma)
       call affinity(1,proj(1,3),evec(1,3),duma,duma)
    end if

    ! The columns of the evec matrix contain the eigenvectors corresponding to
    ! the low, middle, and high eigenvalues, respectively. These evecs have
    ! the highest possible affinity for the lab basis.

    return
  end subroutine proj2evec

  subroutine affinity(m,p,evec1,evec2,evec3)
    !---------------------------------------------------------------------------!
    ! Perform Gram-Schmidt orthogonalization on the columns (or rows) of a
    ! symmetric 3x3 projector [P], with the ordering for the process
    ! determined by "affinity" to the laboratory basis.
    !
    ! Parameters
    ! ----------
    ! m : in, int
    !   rank of the projector
    !      = 1 means the routine will return evec1 as the unit vector
    !        parallel to the largest projection of the lab basis onto
    !        the 1D eigenspace.
    !      = 2 means the routine will eliminate the smallest projector
    !        of the lab basis onto the 2D eigenspace, and then it
    !        will perform Gram-Schmidt orthogonalization on the remaining
    !        projected lab vectors and return the result in evec1 and evec2
    !      = 3 means the projector is the identity, so the routine
    !        will return evec1, evec2, and evec3 equal to the lab
    !        base vectors.
    !  p : in, array
    !    a projector of rank M saved in Voigt ordering
    !
    !  vec1, vec2, vec3 : out, array
    !    the orthonormal vectors.
    !
    ! History
    ! -------
    ! 2004.01.26:Rebecca Brannon:devised and coded algorithm
    ! 2012.05.30:Tim Fuller:converted to f90
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    integer :: m
    real(kind=fp) :: p(6)
    real(kind=fp) :: evec1(3), evec2(3), evec3(3)
    !.......................................................................local
    integer :: i, j, k, n
    real(kind=fp) :: dum, fac
    ! The 3x3 map matrix gives the Voigt ID. map(i,j) equals the 6x1 Voigt ID
    ! of the ij component of the 3x3 projector. Thus, if you desire P(i,j),
    ! you should refer to it as P(map(i,j)). Note that P(map(i,i)) equals
    ! P(i), so we don't use the map when we know we are looking for a diagonal
    ! component.
    integer, parameter :: map(3, 3) = reshape((/1,4,6,4,2,5,6,5,3/), shape(map))
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~proj2evec

    if (m.eq.0) then
       m=nint(p(1)+p(2)+p(3))
       if (m.eq.0) return
    end if

    if (m.eq.1) then
       ! Find column with largest magnitude at beginning. For a projector [P],
       ! the square magnitude of column i simply equals P(i,i).
       i=1
       if (p(2).gt.p(i)) i=2
       if (p(3).gt.p(i)) i=3

       ! At this point, index i is the column number of the largest column.
       dum=one/sqrt(p(i))
       evec1(1)=p(map(1,i))*dum
       evec1(2)=p(map(2,i))*dum
       evec1(3)=p(map(3,i))*dum

    else if (m.eq.2) then
       ! Put column with smallest magnitude at end.
       ! Preserve cyclic order.
       i=1
       j=2
       k=3
       if (p(j).lt.p(k)) then
          n=k
          k=j
          j=i
          i=n
          if (p(j).lt.p(k)) then
             n=k
             k=j
             j=i
             i=n
          end if
       end if
       if (p(i).lt.p(k)) then
          n=i
          i=j
          j=k
          k=n
       end if
       dum=one/sqrt(p(i))
       evec1(1)=p(map(1,i))*dum
       evec1(2)=p(map(2,i))*dum
       evec1(3)=p(map(3,i))*dum

       dum=one/sqrt(p(j)-p(map(i,j))**2/p(i))
       fac=dum*p(map(j,i))/p(i)
       evec2(1)=dum*p(map(1,j))-fac*p(map(1,i))
       evec2(2)=dum*p(map(2,j))-fac*p(map(2,i))
       evec2(3)=dum*p(map(3,j))-fac*p(map(3,i))
       if (m.eq.2) return
       evec3(1)=evec1(2)*evec2(3)-evec1(3)*evec2(2)
       evec3(2)=evec1(3)*evec2(1)-evec1(1)*evec2(3)
       evec3(3)=evec1(1)*evec2(2)-evec1(2)*evec2(1)

    else if (m.eq.3) then
       ! For m=3, the projector is the identity, so simply send back the lab
       ! base vectors.
       evec1(1)=one
       evec1(2)=zero
       evec1(3)=zero
       evec2(1)=zero
       evec2(2)=one
       evec2(3)=zero
       evec3(1)=zero
       evec3(2)=zero
       evec3(3)=one
    end if
    return
  end subroutine affinity

  function randvec(aa)
    ! Generate a random 3 vector
    ! If the optional argument aa is given, a random vector is generated about
    ! the axis contained in aa(1:3) in the cone given by the angle theta in
    ! aa(4)
    implicit none
    !......................................................................passed
    real(kind=fp) :: randvec(3)
    real(kind=fp), optional, intent(in) :: aa(4)
    !.......................................................................local
    real(kind=fp) :: r, s, phi, sinT, theta, h, tc, v(3), L(3, 3), A(3), ea(3)
    real(kind=fp), parameter :: Ez(3)=(/0., 0., 1./)
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ randvec
    if (present(aa)) then
       ! get the preferred axis and normalize it
       A = aa(1:3) / sqrt(sum(aa(1:3) * aa(1:3))); tc = aa(4)
       if (any(A /= A)) then
          ! check for divide by zero
          randvec = zero
       end if
    else
       A = Ez; tc = pi
    end if
    h = cos(tc)

    ! random vector in cone
    r = randnum()
    s = randnum()
    phi = 2. * pi * r
    v(3) = h + (1. - h) * s
    sinT = sqrt(one - v(3) ** 2)
    v(1) = cos(phi) * sinT
    v(2) = sin(phi) * sinT
    v = v / sqrt(sum(v * v))

    ! return if
    !   1) The random vector v is the same as the preferred vector A
    !   2) The preferred axis is lined up with Ez
    !   3) The random vector v is parallel to the preferred vector A
    if (all(abs(v - A) < tiny)) then
       randvec = v
       return
    else if (all(abs(Ez - A) < tiny)) then
       randvec = v
       return
    else if (all(abs(Ez) - abs(A) < tiny)) then
       randvec = v
       randvec(3) = -randvec(3)
       return
    end if

    ! Change of basis to reorient around the prefered axis
    ea = cross(Ez, A, 1)
    theta = acos(sum(Ez * A))
    call aa2dc(ea, theta, L)
    randvec = matmul(L, v)
    randvec = randvec / sqrt(sum(randvec * randvec))
    return
  end function randvec

  subroutine aa2dc(a, t, L)
    implicit none
    !......................................................................passed
    real(kind=fp), intent(in) :: a(3), t
    real(kind=fp), intent(out) :: L(3, 3)
    !.......................................................................local
    real(kind=fp) :: c, s, omc
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ aa2dc
    c = cos(t); s = sin(t); omc = 1. - cos(t)
    L(1, 1) = omc * a(1) * a(1) + c
    L(2, 2) = omc * a(2) * a(2) + c
    L(3, 3) = omc * a(3) * a(3) + c
    L(1, 2) = omc * a(1) * a(2) - s * a(3)
    L(2, 3) = omc * a(2) * a(3) - s * a(1)
    L(3, 1) = omc * a(3) * a(1) - s * a(2)
    L(2, 1) = omc * a(2) * a(1) + s * a(3)
    L(3, 2) = omc * a(3) * a(2) + s * a(1)
    L(1, 3) = omc * a(1) * a(3) + s * a(2)
    return
  end subroutine aa2dc

  function cross(a, b, normalize)
    implicit none
    real(kind=fp) :: cross(3)
    real(kind=fp), intent(in) :: a(3), b(3)
    integer, optional, intent(in) :: normalize
    cross(1) = a(2) * b(3) - a(3) * b(2)
    cross(2) = a(3) * b(1) - a(1) * b(3)
    cross(3) = a(1) * b(2) - a(2) * b(1)
    if (all(abs(cross) < tiny)) return
    if (present(normalize)) cross = cross / sqrt(sum(cross * cross))
    return
  end function cross

  subroutine seedrand(N)
    implicit none
    integer, optional, intent(in) :: N
    integer :: k, M
    integer, allocatable :: seed(:)
    if (present(N)) then
       M = N
    else
       M = 17
    end if
    call random_seed(size=k)
    allocate(seed(1:k))
    seed(:) = 17
    call random_seed(put=seed)
  end subroutine seedrand

  function randnum()
    implicit none
    real(kind=fp) :: randnum
    call random_number(randnum)
    return
  end function randnum

  function reducefac(val, critval, shape)
    !---------------------------------------------------------------------------!
    ! Determine a factor between 0 and 1 such that
    !       if val << critval -> reducefac ~ 1
    !       if val >> critval -> reducefac ~ 0
    ! reducefac starts at 1 and gradually reduces to 0 as val increases. The
    ! manner in which reducefac is decreased is governed by the shape
    ! parameter. when shape = 1 the reduction is roughly linear, when it is 30
    ! or higher it will approximate a heavy-side function.
    !---------------------------------------------------------------------------!
    implicit none
    !......................................................................passed
    real(kind=fp) :: reducefac
    real(kind=fp), intent(in) :: val, critval
    real(kind=fp), intent(in), optional :: shape
    !.......................................................................local
    real(kind=fp) :: dshape
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ reducefac
    if (critval > huge) then
       reducefac = one
    end if
    if (present(shape)) then
       dshape = shape
    else
       dshape = thirty
    end if
    if (dshape == zero) dshape = thirty
    reducefac = (one + exps(-two * dshape)) &
              / (one + exps(-two * dshape * (one - val / critval)))
    return
  end function reducefac

  function exps(arg)
    !---------------------------------------------------------------------------!
    ! Specialized version of exponential to prevent underflow replacement of
    ! EXP(ARG) by zero when ARG is an extraordinarily large negative number.
    ! For all practical purposes, EXPS may be regarded as equivalent to EXP.
    !---------------------------------------------------------------------------!
    implicit none
    !..................................................................parameters
    real(kind=fp), parameter :: eunderflow=-34.53877639491 * one
    real(kind=fp), parameter :: eoverflow=92.1034037 * one
    !......................................................................passed
    real(kind=fp) :: exps
    real(kind=fp), intent(in) :: arg
    !~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~ exps
    ! exps(arg) = exp(arg)
    exps = exp(min(max(arg, eunderflow), eoverflow))
    return
  end function exps

end module tensor_toolkit
